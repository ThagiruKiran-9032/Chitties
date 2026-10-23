import sys
import uuid
from datetime import date, time, datetime, timezone
from decimal import Decimal

from app.core.security import get_password_hash
from app.db.session import SessionLocal
from app.models.organization import Organization, Branch
from app.models.chit_scheme import ChitScheme
from app.models.chit_group import ChitGroup, ChitGroupStatus
from app.models.membership import ChitMembership, MembershipStatus
from app.models.installment import Installment, InstallmentStatus
from app.models.auction import Auction, AuctionStatus
from app.models.user import User, UserRole, KYCStatus


def seed_database():
    """Seeds chitties_db with sample organization, branches, roles, schemes, group, and members."""
    db = SessionLocal()
    try:
        # Check if already seeded
        existing_org = db.query(Organization).filter(Organization.name == "Apex Chits International").first()
        if existing_org:
            existing_accountant = db.query(User).filter(User.email == "accountant@apexchits.com").first()
            if not existing_accountant:
                branch = db.query(Branch).filter(Branch.organization_id == existing_org.id).first()
                accountant = User(
                    organization_id=existing_org.id,
                    branch_id=branch.id if branch else None,
                    full_name="Suresh Menon (Chief Accountant)",
                    email="accountant@apexchits.com",
                    phone="+919900000003",
                    password_hash=get_password_hash("Admin@123"),
                    role=UserRole.ACCOUNTANT,
                    kyc_status=KYCStatus.VERIFIED,
                    is_active=True,
                )
                db.add(accountant)
                db.commit()
                print("Seeded demo Accountant user: accountant@apexchits.com")

            mgr = db.query(User).filter(User.email == "manager@apexchits.com").first()
            if mgr:
                db.query(ChitGroup).filter(ChitGroup.organization_id == existing_org.id, ChitGroup.manager_id == None).update({"manager_id": mgr.id})
                db.commit()
            print("Database already contains Apex Chits International. Skipping duplicate seed.")
            return

        print("Seeding database with enterprise demo data...")

        # 1. Organization
        org = Organization(
            name="Apex Chits International",
            registration_number="REG-APEX-2026-001",
        )
        db.add(org)
        db.commit()
        db.refresh(org)

        # 2. Branch
        branch = Branch(
            organization_id=org.id,
            name="Headquarters Bangalore",
            branch_code="BLR-HQ-01",
        )
        db.add(branch)
        db.commit()
        db.refresh(branch)

        # 3. Super Admin
        super_admin = User(
            full_name="Global Super Admin",
            email="superadmin@chitties.com",
            phone="+919900000000",
            password_hash=get_password_hash("Admin@123"),
            role=UserRole.SUPER_ADMIN,
            kyc_status=KYCStatus.VERIFIED,
            is_active=True,
        )
        db.add(super_admin)

        # 4. Org Admin
        org_admin = User(
            organization_id=org.id,
            branch_id=branch.id,
            full_name="Vikramaditya (Apex Admin)",
            email="admin@apexchits.com",
            phone="+919900000001",
            password_hash=get_password_hash("Admin@123"),
            role=UserRole.ORG_ADMIN,
            kyc_status=KYCStatus.VERIFIED,
            is_active=True,
        )
        db.add(org_admin)

        # 5. Branch Manager
        branch_mgr = User(
            organization_id=org.id,
            branch_id=branch.id,
            full_name="Rajesh Rao (Branch Mgr)",
            email="manager@apexchits.com",
            phone="+919900000002",
            password_hash=get_password_hash("Admin@123"),
            role=UserRole.BRANCH_MANAGER,
            kyc_status=KYCStatus.VERIFIED,
            is_active=True,
        )
        db.add(branch_mgr)

        # 5b. Accountant
        accountant = User(
            organization_id=org.id,
            branch_id=branch.id,
            full_name="Suresh Menon (Chief Accountant)",
            email="accountant@apexchits.com",
            phone="+919900000003",
            password_hash=get_password_hash("Admin@123"),
            role=UserRole.ACCOUNTANT,
            kyc_status=KYCStatus.VERIFIED,
            is_active=True,
        )
        db.add(accountant)

        # 6. Subscribers (5 KYC-verified subscribers)
        sub_data = [
            ("Kiran Kumar (Ticket 1)", "kiran.subscriber@gmail.com", "+919876543210"),
            ("Priya Sharma (Ticket 2)", "priya.sharma@example.com", "+919876543211"),
            ("Rahul Verma (Ticket 3)", "rahul.verma@example.com", "+919876543212"),
            ("Anita Desai (Ticket 4)", "anita.desai@example.com", "+919876543213"),
            ("Vikram Singh (Ticket 5)", "vikram.singh@example.com", "+919876543214"),
        ]

        subscribers = []
        for name, email, phone in sub_data:
            sub = User(
                organization_id=org.id,
                branch_id=branch.id,
                full_name=name,
                email=email,
                phone=phone,
                password_hash=get_password_hash("Sub@123"),
                role=UserRole.SUBSCRIBER,
                kyc_status=KYCStatus.VERIFIED,
                is_active=True,
            )
            db.add(sub)
            subscribers.append(sub)

        db.commit()
        for s in subscribers:
            db.refresh(s)

        # 7. Chit Scheme (1 Lakh, 5 Months, ₹20,000 / month)
        scheme = ChitScheme(
            organization_id=org.id,
            name="Apex Gold 1 Lakh (5M)",
            total_value=Decimal("100000.00"),
            duration_months=5,
            monthly_installment=Decimal("20000.00"),
            foreman_commission_pct=Decimal("5.00"),
            min_bid_discount_pct=Decimal("5.00"),
            max_bid_discount_pct=Decimal("30.00"),
            foreman_month_one_reserved=False,
            is_active=True,
        )
        db.add(scheme)
        db.commit()
        db.refresh(scheme)

        # 8. Chit Group (ACTIVE, with 5 tickets filled)
        group = ChitGroup(
            organization_id=org.id,
            branch_id=branch.id,
            scheme_id=scheme.id,
            manager_id=branch_mgr.id,
            group_code="APEX-GOLD-2026",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 10, 31),
            current_month=1,
            auction_day_of_month=15,
            auction_time=time(16, 0),
            status=ChitGroupStatus.ACTIVE,
        )
        db.add(group)
        db.commit()
        db.refresh(group)

        # 9. Enroll all 5 members & generate Month 1 Installment Dues
        memberships = []
        for i, sub in enumerate(subscribers, start=1):
            mem = ChitMembership(
                chit_group_id=group.id,
                user_id=sub.id,
                ticket_number=i,
                status=MembershipStatus.ACTIVE,
            )
            db.add(mem)
            db.commit()
            db.refresh(mem)
            memberships.append(mem)

            # Month 1 Installment
            inst = Installment(
                chit_group_id=group.id,
                chit_membership_id=mem.id,
                month_number=1,
                due_date=date(2026, 6, 1),
                gross_amount=Decimal("20000.00"),
                dividend_amount=Decimal("0.00"),
                penalty_amount=Decimal("0.00"),
                net_due_amount=Decimal("20000.00"),
                paid_amount=Decimal("0.00"),
                status=InstallmentStatus.UNPAID,
            )
            db.add(inst)

        # 10. Month 1 Auction (Ready for live reverse bidding)
        auction = Auction(
            chit_group_id=group.id,
            month_number=1,
            scheduled_at=datetime(2026, 6, 15, 16, 0, tzinfo=timezone.utc),
            status=AuctionStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
            is_foreman_month=False,
        )
        db.add(auction)
        db.commit()

        print("Database seeded successfully with Apex Chits demo ecosystem!")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
