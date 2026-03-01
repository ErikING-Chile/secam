"""
Secam Edge Agent - RTSP Camera Processor with Face Detection/Recognition

This agent runs on the edge (camera location) and:
1. Connects to RTSP cameras
2. Captures frames at regular intervals
3. Detects faces using face_recognition
4. Matches against known faces from the cloud API
5. Sends events to the cloud API
"""
import os
import time
import json
import base64
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

import cv2
import face_recognition
import numpy as np
import requests
from cryptography.fernet import Fernet
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()


class EdgeAgentConfig:
    """Edge Agent configuration."""
    
    # Cloud API settings
    CLOUD_API_URL = os.getenv('CLOUD_API_URL', 'http://localhost:8000')
    EDGE_AGENT_ID = os.getenv('EDGE_AGENT_ID', '')
    EDGE_AGENT_SECRET = os.getenv('EDGE_AGENT_SECRET', '')
    
    # Processing settings
    FRAME_INTERVAL = int(os.getenv('FRAME_INTERVAL', '5'))  # seconds
    FACE_DETECTION_THRESHOLD = float(os.getenv('FACE_DETECTION_THRESHOLD', '0.6'))
    FACE_RECOGNITION_THRESHOLD = float(os.getenv('FACE_RECOGNITION_THRESHOLD', '0.6'))
    
    # Storage
    STORAGE_PATH = os.getenv('STORAGE_PATH', '/tmp/secam/faces')


class FaceRecognizer:
    """Face recognition handler."""
    
    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold
        self.known_encodings = []
        self.known_person_ids = []
        self.known_person_names = []
        
    def load_known_faces(self, known_faces: list):
        """Load known faces from API response."""
        self.known_encodings = []
        self.known_person_ids = []
        self.known_person_names = []
        
        for person in known_faces:
            for embedding in person.get('embeddings', []):
                try:
                    encoding = json.loads(embedding['embedding_vector'])
                    self.known_encodings.append(np.array(encoding))
                    self.known_person_ids.append(person['id'])
                    self.known_person_names.append(person['name'])
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning(f"Failed to load embedding for {person.get('name')}: {e}")
        
        logger.info(f"Loaded {len(self.known_encodings)} known face encodings")
    
    def detect_and_recognize(self, frame) -> tuple:
        """
        Detect and recognize faces in a frame.
        Returns: (face_locations, face_names, face_confidences)
        """
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        face_locations = face_recognition.face_locations(rgb_frame)
        
        if not face_locations:
            return [], [], []
        
        # Get face encodings
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)
        
        names = []
        confidences = []
        
        for encoding in face_encodings:
            if not self.known_encodings:
                names.append("unknown")
                confidences.append(0.0)
                continue
            
            # Compare with known faces
            matches = face_recognition.compare_faces(
                self.known_encodings, 
                encoding, 
                tolerance=self.threshold
            )
            
            face_distances = face_recognition.face_distance(
                self.known_encodings, 
                encoding
            )
            
            if True in matches:
                best_match_index = np.argmin(face_distances)
                confidence = 1.0 - face_distances[best_match_index]
                
                if confidence >= self.threshold:
                    names.append(self.known_person_names[best_match_index])
                    confidences.append(float(confidence))
                else:
                    names.append("unknown")
                    confidences.append(float(confidence))
            else:
                names.append("unknown")
                confidences.append(0.0)
        
        return face_locations, names, confidences


class CameraProcessor:
    """Process a single RTSP camera stream."""
    
    def __init__(
        self, 
        camera_id: str,
        rtsp_url: str,
        encryption_key: str,
        agent_id: str,
        api_url: str
    ):
        self.camera_id = camera_id
        self.rtsp_url = self._decrypt_rtsp(rtsp_url, encryption_key)
        self.agent_id = agent_id
        self.api_url = api_url
        self.face_recognizer = FaceRecognizer()
        self.running = False
        self._auth_token = None
        
    def _decrypt_rtsp(self, encrypted_url: str, key: str) -> str:
        """Decrypt RTSP URL."""
        try:
            fernet = Fernet(key.encode())
            return fernet.decrypt(encrypted_url.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt RTSP URL: {e}")
            return encrypted_url
    
    def authenticate(self):
        """Authenticate with the cloud API."""
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/edge/auth",
                json={
                    "agent_id": self.agent_id,
                    "secret": os.getenv('EDGE_AGENT_SECRET', '')
                },
                timeout=10
            )
            if response.status_code == 200:
                self._auth_token = response.json().get('access_token')
                logger.info(f"Authenticated successfully for camera {self.camera_id}")
            else:
                logger.error(f"Authentication failed: {response.status_code}")
        except Exception as e:
            logger.error(f"Authentication error: {e}")
    
    def fetch_known_faces(self):
        """Fetch known faces from the cloud API."""
        if not self._auth_token:
            return []
        
        try:
            response = requests.get(
                f"{self.api_url}/api/v1/persons",
                headers={"Authorization": f"Bearer {self._auth_token}"},
                timeout=30
            )
            if response.status_code == 200:
                persons = response.json()
                
                for person in persons:
                    emb_response = requests.get(
                        f"{self.api_url}/api/v1/persons/{person['id']}/embeddings",
                        headers={"Authorization": f"Bearer {self._auth_token}"},
                        timeout=10
                    )
                    if emb_response.status_code == 200:
                        person['embeddings'] = emb_response.json()
                
                return persons
            else:
                logger.error(f"Failed to fetch persons: {response.status_code}")
        except Exception as e:
            logger.error(f"Error fetching known faces: {e}")
        
        return []
    
    def send_event(self, event_type: str, person_name: str = None, confidence: float = None, snapshot_path: str = None):
        """Send event to the cloud API."""
        if not self._auth_token:
            logger.warning("Not authenticated, cannot send event")
            return
        
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/events",
                headers={"Authorization": f"Bearer {self._auth_token}"},
                json={
                    "camera_id": self.camera_id,
                    "type": event_type,
                    "confidence": confidence,
                    "snapshot_path": snapshot_path,
                    "metadata": {"person_name": person_name} if person_name else None
                },
                timeout=10
            )
            if response.status_code in (200, 201):
                logger.info(f"Event sent: {event_type} - {person_name}")
            else:
                logger.error(f"Failed to send event: {response.status_code}")
        except Exception as e:
            logger.error(f"Error sending event: {e}")
    
    def save_snapshot(self, frame) -> Optional[str]:
        """Save a snapshot of the frame."""
        try:
            os.makedirs(EdgeAgentConfig.STORAGE_PATH, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.camera_id}_{timestamp}.jpg"
            filepath = os.path.join(EdgeAgentConfig.STORAGE_PATH, filename)
            cv2.imwrite(filepath, frame)
            return filepath
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")
            return None
    
    def process_frame(self, frame):
        """Process a single frame for face detection/recognition."""
        locations, names, confidences = self.face_recognizer.detect_and_recognize(frame)
        
        for name, confidence in zip(names, confidences):
            if name == "unknown":
                self.send_event(
                    event_type="unknown_face",
                    person_name=None,
                    confidence=confidence,
                    snapshot_path=self.save_snapshot(frame)
                )
            else:
                self.send_event(
                    event_type="known_face",
                    person_name=name,
                    confidence=confidence,
                    snapshot_path=self.save_snapshot(frame)
                )
    
    def run(self):
        """Main processing loop for this camera."""
        self.authenticate()
        
        # Load known faces
        known_faces = self.fetch_known_faces()
        self.face_recognizer.load_known_faces(known_faces)
        
        # Connect to RTSP stream
        cap = cv2.VideoCapture(self.rtsp_url)
        
        if not cap.isOpened():
            logger.error(f"Failed to connect to RTSP stream: {self.rtsp_url}")
            return
        
        logger.info(f"Started processing camera {self.camera_id}")
        
        self.running = True
        last_processed = time.time()
        
        while self.running:
            ret, frame = cap.read()
            
            if not ret:
                logger.warning(f"Failed to read frame from {self.camera_id}")
                time.sleep(1)
                continue
            
            # Process frame at intervals
            current_time = time.time()
            if current_time - last_processed >= EdgeAgentConfig.FRAME_INTERVAL:
                try:
                    self.process_frame(frame)
                except Exception as e:
                    logger.error(f"Error processing frame: {e}")
                
                last_processed = current_time
            
            time.sleep(0.1)
        
        cap.release()
        logger.info(f"Stopped processing camera {self.camera_id}")
    
    def stop(self):
        """Stop processing."""
        self.running = False


class EdgeAgent:
    """Main Edge Agent class that manages multiple cameras."""
    
    def __init__(self):
        self.config = EdgeAgentConfig()
        self.cameras = {}
        self.threads = []
        
    def fetch_cameras(self):
        """Fetch assigned cameras from the cloud API."""
        if not self.config.EDGE_AGENT_ID:
            logger.warning("EDGE_AGENT_ID not configured")
            return []
        
        try:
            # First authenticate
            auth_response = requests.post(
                f"{self.config.CLOUD_API_URL}/api/v1/edge/auth",
                json={
                    "agent_id": self.config.EDGE_AGENT_ID,
                    "secret": self.config.EDGE_AGENT_SECRET
                },
                timeout=10
            )
            
            if auth_response.status_code != 200:
                logger.error(f"Authentication failed: {auth_response.status_code}")
                return []
            
            token = auth_response.json().get('access_token')
            
            # Fetch cameras
            response = requests.get(
                f"{self.config.CLOUD_API_URL}/api/v1/cameras",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch cameras: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching cameras: {e}")
        
        return []
    
    def start(self):
        """Start the edge agent."""
        logger.info("Starting Secam Edge Agent...")
        
        while True:
            try:
                cameras = self.fetch_cameras()
                
                for camera in cameras:
                    camera_id = camera['id']
                    
                    if camera_id not in self.cameras:
                        # Get encrypted RTSP URL from camera
                        # In a real implementation, we'd fetch this securely
                        logger.info(f"Starting processor for camera: {camera['name']}")
                        
                        # For demo purposes, we'd need the encrypted RTSP from API
                        # This would be added to the API response
                        
                # Refresh cameras periodically
                time.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)
    
    def stop(self):
        """Stop all camera processors."""
        for processor in self.cameras.values():
            processor.stop()
        self.cameras.clear()


def main():
    """Main entry point."""
    agent = EdgeAgent()
    agent.start()


if __name__ == "__main__":
    main()
