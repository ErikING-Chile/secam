"use client";

import { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import toast, { Toaster } from "react-hot-toast";
import WebRTCFeed from "@/components/WebRTCFeed";

function SnapshotFeed({ cameraId }: { cameraId: string }) {
  const imgRef = useRef<HTMLImageElement>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    
    const updateSnapshot = () => {
      if (imgRef.current && token) {
        imgRef.current.src = `${API_URL}/cameras/${cameraId}/snapshot?token=${token}&t=${Date.now()}`;
      }
    };

    updateSnapshot();
    setLoading(false);

    const interval = setInterval(updateSnapshot, 1000);

    return () => clearInterval(interval);
  }, [cameraId]);

  return (
    <div className="relative w-full h-full">
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
        </div>
      )}
      <img
        ref={imgRef}
        alt="Live feed"
        className="w-full h-full object-cover"
        style={{ backgroundColor: '#000' }}
        onError={() => setError(true)}
      />
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50">
          <p className="text-white text-sm">Error cargando stream</p>
        </div>
      )}
    </div>
  );
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function SnapshotFeed({ cameraId }: { cameraId: string }) {
  const imgRef = useRef<HTMLImageElement>(null);
  const [error, setError] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    
    const updateSnapshot = () => {
      if (imgRef.current && token) {
        imgRef.current.src = `${API_URL}/cameras/${cameraId}/snapshot?token=${token}&t=${Date.now()}`;
      }
    };

    updateSnapshot();
    setLoading(false);

    const interval = setInterval(updateSnapshot, 1000);

    return () => clearInterval(interval);
  }, [cameraId]);

  return (
    <div className="relative w-full h-full">
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
        </div>
      )}
      <img
        ref={imgRef}
        alt="Live feed"
        className="w-full h-full object-cover"
        style={{ backgroundColor: '#000' }}
        onError={() => setError(true)}
      />
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50">
          <p className="text-white text-sm">Error cargando stream</p>
        </div>
      )}
    </div>
  );
}

interface UserInfo {
  id: string;
  tenant_id: string;
  email: string;
  role: string;
  tenant_name: string;
  tenant_slug: string;
  tenant_plan: string;
}

interface Camera {
  id: string;
  tenant_id: string;
  name: string;
  status: string;
  location: string | null;
  created_at: string;
}

interface Event {
  id: string;
  tenant_id: string;
  camera_id: string | null;
  type: string;
  confidence: number | null;
  snapshot_path: string | null;
  created_at: string;
}

interface EventStats {
  total_events: number;
  events_today: number;
  events_by_type: Record<string, number>;
}

interface Person {
  id: string;
  tenant_id: string;
  name: string;
  notes: string | null;
  status: string;
  created_at: string;
}

interface PersonStats {
  total_persons: number;
  persons_with_faces: number;
}

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [events, setEvents] = useState<Event[]>([]);
  const [eventStats, setEventStats] = useState<EventStats | null>(null);
  const [persons, setPersons] = useState<Person[]>([]);
  const [personStats, setPersonStats] = useState<PersonStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const [showCameraForm, setShowCameraForm] = useState(false);
  const [editingCamera, setEditingCamera] = useState<Camera | null>(null);
  const [cameraForm, setCameraForm] = useState({ name: "", rtsp_url: "", location: "" });

  const [showPersonForm, setShowPersonForm] = useState(false);
  const [personForm, setPersonForm] = useState({ name: "", notes: "" });

  const [showLiveView, setShowLiveView] = useState(false);
  const [selectedCamera, setSelectedCamera] = useState<Camera | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    const fetchData = async () => {
      try {
        const response = await axios.get(`${API_URL}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setUser(response.data);

        await Promise.all([
          fetchCameras(token),
          fetchEvents(token),
          fetchPersonStats(token),
          fetchPersons(token),
        ]);
      } catch (error: any) {
        if (error.response?.status === 401) {
          toast.error("Sesión expirada. Por favor iniciá sesión de nuevo.");
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          router.push("/login");
        } else {
          toast.error("Error al cargar datos");
        }
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [router]);

  const fetchCameras = async (token: string) => {
    const response = await axios.get(`${API_URL}/cameras`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    setCameras(response.data);
  };

  const fetchEvents = async (token: string) => {
    const [eventsRes, statsRes] = await Promise.all([
      axios.get(`${API_URL}/events?limit=20`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
      axios.get(`${API_URL}/events/stats`, {
        headers: { Authorization: `Bearer ${token}` },
      }),
    ]);
    setEvents(eventsRes.data);
    setEventStats(statsRes.data);
  };

  const fetchPersons = async (token: string) => {
    const response = await axios.get(`${API_URL}/persons`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    setPersons(response.data);
  };

  const fetchPersonStats = async (token: string) => {
    const response = await axios.get(`${API_URL}/persons/stats`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    setPersonStats(response.data);
  };

  const handleLogout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    router.push("/login");
  };

  const handleCreateCamera = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = localStorage.getItem("access_token");
    if (!token) {
      toast.error("Sesión expirada");
      router.push("/login");
      return;
    }

    try {
      await axios.post(
        `${API_URL}/cameras`,
        {
          name: cameraForm.name,
          rtsp_url: cameraForm.rtsp_url,
          location: cameraForm.location || null,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      toast.success("Cámara creada exitosamente");
      setShowCameraForm(false);
      setCameraForm({ name: "", rtsp_url: "", location: "" });
      fetchCameras(token);
    } catch (error: any) {
      if (error.response?.status === 401) {
        toast.error("Sesión expirada. Por favor iniciá sesión de nuevo.");
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        router.push("/login");
      } else {
        toast.error(error.response?.data?.detail || "Error al crear cámara");
      }
    }
  };

  const handleDeleteCamera = async (cameraId: string) => {
    if (!confirm("¿Estás seguro de eliminar esta cámara?")) return;
    
    const token = localStorage.getItem("access_token");
    if (!token) return;

    try {
      await axios.delete(`${API_URL}/cameras/${cameraId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success("Cámara eliminada");
      fetchCameras(token);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Error al eliminar cámara");
    }
  };

  const handleUpdateCamera = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingCamera) return;
    
    const token = localStorage.getItem("access_token");
    if (!token) {
      toast.error("Sesión expirada. Por favor iniciá sesión de nuevo.");
      router.push("/login");
      return;
    }

    try {
      await axios.put(
        `${API_URL}/cameras/${editingCamera.id}`,
        {
          name: cameraForm.name,
          rtsp_url: cameraForm.rtsp_url || undefined,
          location: cameraForm.location || null,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      toast.success("Cámara actualizada");
      setEditingCamera(null);
      setCameraForm({ name: "", rtsp_url: "", location: "" });
      fetchCameras(token);
    } catch (error: any) {
      if (error.response?.status === 401) {
        toast.error("Sesión expirada. Por favor iniciá sesión de nuevo.");
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        router.push("/login");
      } else {
        toast.error(error.response?.data?.detail || "Error al actualizar cámara");
      }
    }
  };

  const handleCreatePerson = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = localStorage.getItem("access_token");
    
    if (!token) return;

    try {
      await axios.post(
        `${API_URL}/persons`,
        {
          name: personForm.name,
          notes: personForm.notes || null,
        },
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );
      toast.success("Persona creada exitosamente");
      setShowPersonForm(false);
      setPersonForm({ name: "", notes: "" });
      fetchPersons(token);
      fetchPersonStats(token);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Error al crear persona");
    }
  };

  const handleDeletePerson = async (personId: string) => {
    if (!confirm("¿Estás seguro de eliminar esta persona y todos sus rostros?")) return;
    
    const token = localStorage.getItem("access_token");
    if (!token) return;

    try {
      await axios.delete(`${API_URL}/persons/${personId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      toast.success("Persona eliminada");
      fetchPersons(token);
      fetchPersonStats(token);
    } catch (error: any) {
      toast.error(error.response?.data?.detail || "Error al eliminar persona");
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Cargando...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Toaster position="top-center" />
      
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center">
              <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">Secam</h1>
              <p className="text-sm text-gray-500">{user.tenant_name}</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-3">
            {user.role === 'super_admin' && (
              <button
                onClick={() => router.push("/admin")}
                className="px-4 py-2 text-sm text-red-600 hover:text-red-700 font-medium"
              >
                Panel Admin
              </button>
            )}
            <button
              onClick={handleLogout}
              className="px-4 py-2 text-sm text-gray-700 hover:text-gray-900 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
            >
              Cerrar sesión
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Card */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            ¡Bienvenido a Secam! 👋
          </h2>
          <p className="text-gray-600 mb-6">
            Tu plataforma de videovigilancia inteligente está lista.
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* User Info */}
            <div className="bg-blue-50 rounded-xl p-6">
              <div className="flex items-center space-x-3 mb-3">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                <h3 className="font-semibold text-gray-900">Usuario</h3>
              </div>
              <p className="text-gray-700">{user.email}</p>
              <p className="text-sm text-blue-600 mt-1 capitalize">{user.role.replace('_', ' ')}</p>
            </div>

            {/* Tenant Info */}
            <div className="bg-green-50 rounded-xl p-6">
              <div className="flex items-center space-x-3 mb-3">
                <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
                <h3 className="font-semibold text-gray-900">Organización</h3>
              </div>
              <p className="text-gray-700">{user.tenant_name}</p>
              <p className="text-sm text-green-600 mt-1">/{user.tenant_slug}</p>
            </div>

            {/* Plan Info */}
            <div className="bg-purple-50 rounded-xl p-6">
              <div className="flex items-center space-x-3 mb-3">
                <svg className="w-6 h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                </svg>
                <h3 className="font-semibold text-gray-900">Plan</h3>
              </div>
              <p className="text-gray-700 capitalize">{user.tenant_plan}</p>
              <p className="text-sm text-purple-600 mt-1">Fase 7 - Producción</p>
            </div>
          </div>
        </div>

        {/* Cameras Section */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-bold text-gray-900">Cámaras</h3>
            <button
              onClick={() => setShowCameraForm(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition flex items-center space-x-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span>Agregar Cámara</span>
            </button>
          </div>

          {cameras.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              <p>No hay cámaras configuradas</p>
              <p className="text-sm mt-1">Agrega tu primera cámara RTSP</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {cameras.map((camera) => (
                <div key={camera.id} className="border border-gray-200 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      <div className={`w-3 h-3 rounded-full ${camera.status === 'online' ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                      <h4 className="font-semibold text-gray-900">{camera.name}</h4>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => {
                          setSelectedCamera(camera);
                          setShowLiveView(true);
                        }}
                        className="text-blue-500 hover:text-blue-700"
                        title="Ver en vivo"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => {
                          setEditingCamera(camera);
                          setCameraForm({
                            name: camera.name,
                            rtsp_url: "",
                            location: camera.location || ""
                          });
                        }}
                        className="text-gray-400 hover:text-gray-600"
                        title="Editar"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                      </button>
                      <button
                        onClick={() => handleDeleteCamera(camera.id)}
                        className="text-gray-400 hover:text-red-600"
                        title="Eliminar"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                  {camera.location && (
                    <p className="text-sm text-gray-500 mb-2">{camera.location}</p>
                  )}
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    camera.status === 'online' 
                      ? 'bg-green-100 text-green-700' 
                      : 'bg-gray-100 text-gray-600'
                  }`}>
                    {camera.status === 'online' ? 'En línea' : 'Desconectada'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Events Section */}
        <div className="bg-white rounded-2xl shadow-lg p-8 mb-8">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-bold text-gray-900">Eventos Recientes</h3>
          </div>

          {eventStats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="bg-blue-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-blue-600">{eventStats.total_events}</p>
                <p className="text-sm text-gray-600">Total</p>
              </div>
              <div className="bg-green-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-green-600">{eventStats.events_today}</p>
                <p className="text-sm text-gray-600">Hoy</p>
              </div>
              {eventStats.events_by_type && Object.entries(eventStats.events_by_type).map(([type, count]) => (
                <div key={type} className="bg-purple-50 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-purple-600">{count}</p>
                  <p className="text-sm text-gray-600 capitalize">{type.replace('_', ' ')}</p>
                </div>
              ))}
            </div>
          )}

          {events.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p>No hay eventos registrados</p>
            </div>
          ) : (
            <div className="space-y-3">
              {events.map((event) => (
                <div key={event.id} className="flex items-center justify-between p-4 border border-gray-100 rounded-lg hover:bg-gray-50">
                  <div className="flex items-center space-x-4">
                    <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                      event.type === 'motion' ? 'bg-yellow-100' :
                      event.type === 'face_detected' ? 'bg-blue-100' :
                      event.type === 'person_recognized' ? 'bg-green-100' :
                      'bg-gray-100'
                    }`}>
                      {event.type === 'motion' ? '👤' : 
                       event.type === 'face_detected' ? '👁️' :
                       event.type === 'person_recognized' ? '✅' : '📹'}
                    </div>
                    <div>
                      <p className="font-medium text-gray-900 capitalize">{event.type.replace('_', ' ')}</p>
                      <p className="text-sm text-gray-500">{new Date(event.created_at).toLocaleString()}</p>
                    </div>
                  </div>
                  {event.confidence && (
                    <span className="text-sm text-gray-500">{Math.round(event.confidence * 100)}%</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Persons Section */}
        <div className="bg-white rounded-2xl shadow-lg p-8">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-xl font-bold text-gray-900">Personas Registradas</h3>
            <button
              onClick={() => setShowPersonForm(true)}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition flex items-center space-x-2"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              <span>Agregar Persona</span>
            </button>
          </div>

          {personStats && (
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-blue-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-blue-600">{personStats.total_persons}</p>
                <p className="text-sm text-gray-600">Total</p>
              </div>
              <div className="bg-green-50 rounded-lg p-4 text-center">
                <p className="text-2xl font-bold text-green-600">{personStats.persons_with_faces}</p>
                <p className="text-sm text-gray-600">Con rostro registrado</p>
              </div>
            </div>
          )}

          {persons.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <svg className="w-16 h-16 mx-auto mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
              <p>No hay personas registradas</p>
              <p className="text-sm mt-1">Agrega personas para reconocimiento facial</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {persons.map((person) => (
                <div key={person.id} className="border border-gray-200 rounded-xl p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center">
                        <span className="text-green-600 font-bold">{person.name.charAt(0).toUpperCase()}</span>
                      </div>
                      <div>
                        <h4 className="font-semibold text-gray-900">{person.name}</h4>
                        <span className={`text-xs px-2 py-1 rounded-full ${
                          person.status === 'active' 
                            ? 'bg-green-100 text-green-700' 
                            : 'bg-gray-100 text-gray-600'
                        }`}>
                          {person.status === 'active' ? 'Activa' : 'Inactiva'}
                        </span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleDeletePerson(person.id)}
                      className="text-gray-400 hover:text-red-600"
                      title="Eliminar"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                  {person.notes && (
                    <p className="text-sm text-gray-500 mt-2">{person.notes}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Camera Form Modal */}
      {showCameraForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Agregar Cámara</h3>
            <form onSubmit={handleCreateCamera} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
                <input
                  type="text"
                  value={cameraForm.name}
                  onChange={(e) => setCameraForm({ ...cameraForm, name: e.target.value })}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Cámara frontal"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">URL RTSP</label>
                <input
                  type="text"
                  value={cameraForm.rtsp_url}
                  onChange={(e) => setCameraForm({ ...cameraForm, rtsp_url: e.target.value })}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="rtsp://192.168.1.100:554/stream"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Ubicación</label>
                <input
                  type="text"
                  value={cameraForm.location}
                  onChange={(e) => setCameraForm({ ...cameraForm, location: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="Entrada principal"
                />
              </div>
              <div className="flex space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowCameraForm(false);
                    setCameraForm({ name: "", rtsp_url: "", location: "" });
                  }}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Crear
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Camera Modal */}
      {editingCamera && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Editar Cámara</h3>
            <form onSubmit={handleUpdateCamera} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
                <input
                  type="text"
                  value={cameraForm.name}
                  onChange={(e) => setCameraForm({ ...cameraForm, name: e.target.value })}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  URL RTSP (dejar vacío para mantener la actual)
                </label>
                <input
                  type="text"
                  value={cameraForm.rtsp_url}
                  onChange={(e) => setCameraForm({ ...cameraForm, rtsp_url: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="rtsp://192.168.1.100:554/stream"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Ubicación</label>
                <input
                  type="text"
                  value={cameraForm.location}
                  onChange={(e) => setCameraForm({ ...cameraForm, location: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="flex space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setEditingCamera(null);
                    setCameraForm({ name: "", rtsp_url: "", location: "" });
                  }}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
                >
                  Actualizar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Person Form Modal */}
      {showPersonForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl p-6 max-w-md w-full">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Agregar Persona</h3>
            <form onSubmit={handleCreatePerson} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nombre</label>
                <input
                  type="text"
                  value={personForm.name}
                  onChange={(e) => setPersonForm({ ...personForm, name: e.target.value })}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                  placeholder="Juan Pérez"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notas (opcional)</label>
                <textarea
                  value={personForm.notes}
                  onChange={(e) => setPersonForm({ ...personForm, notes: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500"
                  placeholder="Descripción adicional..."
                  rows={3}
                />
              </div>
              <div className="flex space-x-3 pt-2">
                <button
                  type="button"
                  onClick={() => {
                    setShowPersonForm(false);
                    setPersonForm({ name: "", notes: "" });
                  }}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
                >
                  Crear
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Live View Modal */}
      {showLiveView && selectedCamera && (
        <div className="fixed inset-0 bg-black bg-opacity-90 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-2xl p-4 max-w-4xl w-full">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold text-gray-900">{selectedCamera.name}</h3>
              <button
                onClick={() => {
                  setShowLiveView(false);
                  setSelectedCamera(null);
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="bg-gray-900 rounded-lg aspect-video flex items-center justify-center overflow-hidden">
              {selectedCamera ? (
                <SnapshotFeed cameraId={selectedCamera.id} />
              ) : (
                <div className="text-center text-white">
                  <svg className="w-16 h-16 mx-auto mb-4 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  <p className="text-gray-400">Cámara desconectada</p>
                  <p className="text-sm text-gray-500 mt-2">La cámara está fuera de línea</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
