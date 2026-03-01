#!/usr/bin/env python3
"""Seed script to create demo data for Secam."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db import SessionLocal, engine, Base
from app.models import Tenant, User, UserRole, UserStatus, TenantStatus, PlanType
from app.auth import get_password_hash

def seed():
    """Create demo tenant and users."""
    print("🌱 Seeding database...")
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Check if demo tenant already exists
        existing = db.query(Tenant).filter(Tenant.slug == "demo").first()
        if existing:
            print("⚠️  Demo tenant already exists, skipping...")
            return
        
        # Create demo tenant
        tenant = Tenant(
            name="Demo Organization",
            slug="demo",
            plan=PlanType.PRO,
            status=TenantStatus.ACTIVE
        )
        db.add(tenant)
        db.flush()
        
        # Create demo admin user
        admin = User(
            tenant_id=tenant.id,
            email="admin@demo.com",
            password_hash=get_password_hash("demo123"),
            role=UserRole.TENANT_ADMIN,
            status=UserStatus.ACTIVE
        )
        db.add(admin)
        
        # Create demo regular user
        user = User(
            tenant_id=tenant.id,
            email="user@demo.com",
            password_hash=get_password_hash("user123"),
            role=UserRole.TENANT_USER,
            status=UserStatus.ACTIVE
        )
        db.add(user)
        
        # Create super admin
        super_admin = User(
            tenant_id=tenant.id,
            email="superadmin@secam.io",
            password_hash=get_password_hash("superadmin123"),
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE
        )
        db.add(super_admin)
        
        db.commit()
        
        print("✅ Demo data created successfully!")
        print("\n📧 Demo Accounts:")
        print("  • Super Admin: superadmin@secam.io / superadmin123")
        print("  • Tenant Admin: admin@demo.com / demo123")
        print("  • User: user@demo.com / user123")
        print("\n🔒 Change these passwords in production!")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
