import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session, selectinload

from app.models.compliance import (
    SecurityDeposit,
    RegistrarFiling,
    DepositType,
    LienStatus,
    FilingType,
    FilingStatus,
)
from app.models.chit_group import ChitGroup, ChitGroupStatus
from app.models.chit_scheme import ChitScheme
from app.models.auction import Auction, Bid, AuctionStatus
from app.models.installment import Installment, InstallmentStatus
from app.models.payout import Payout, PayoutStatus
from app.models.membership import ChitMembership, MembershipStatus
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.compliance import (
    SecurityDepositCreate,
    SecurityDepositVerifyRequest,
    RegistrarFilingCreate,
    RegistrarFilingUpdate,
)


class ComplianceService:
    """
    Service enforcing the Chit Funds Act, 1982 regulatory requirements:
    - Section 20 Foreman Security Deposit (100% lien pledge before circle launch)
    - Statutory Registrar Filings & Form XIV (Auction Minutes) generation
    - Double-entry Circle Financial Balance Sheet & Delinquency Aging
    """

    # =========================================================================
    # SECTION 20 SECURITY DEPOSITS
    # =========================================================================

    @staticmethod
    def lodge_security_deposit(
        db: Session,
        organization_id: uuid.UUID,
        data: SecurityDepositCreate,
        actor_id: Optional[uuid.UUID] = None,
    ) -> SecurityDeposit:
        group = db.execute(
            select(ChitGroup)
            .options(selectinload(ChitGroup.scheme))
            .where(
                ChitGroup.id == data.group_id,
                ChitGroup.organization_id == organization_id,
            )
        ).scalar_one_or_none()

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chit circle not found in this organization.",
            )

        # Section 20 mandate: Amount must cover 100% of the aggregate chit value
        required_chit_value = Decimal(str(group.scheme.total_value))
        deposit_amount = Decimal(str(data.amount))
        if deposit_amount < required_chit_value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Under Section 20 of the Chit Funds Act 1982, statutory security deposit "
                    f"must be 100% of the chit value (₹{required_chit_value:,.2f}). "
                    f"Provided amount is ₹{deposit_amount:,.2f}."
                ),
            )

        if data.maturity_date <= data.deposit_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deposit maturity date must be strictly after the deposit date.",
            )

        deposit = SecurityDeposit(
            organization_id=organization_id,
            group_id=data.group_id,
            deposit_type=data.deposit_type,
            bank_name=data.bank_name,
            account_or_fdr_number=data.account_or_fdr_number,
            amount=deposit_amount,
            deposit_date=data.deposit_date,
            maturity_date=data.maturity_date,
            registrar_order_reference=data.registrar_order_reference,
            lien_status=LienStatus.PENDING,
            remarks=data.remarks,
        )
        db.add(deposit)
        db.flush()

        # Audit
        db.add(
            AuditLog(
                organization_id=organization_id,
                user_id=actor_id,
                action="LODGE_SECURITY_DEPOSIT",
                entity_type="SecurityDeposit",
                entity_id=deposit.id,
                changes_json={
                    "group_code": group.group_code,
                    "fdr_number": deposit.account_or_fdr_number,
                    "amount": str(deposit.amount),
                    "bank_name": deposit.bank_name,
                },
            )
        )
        db.commit()
        db.refresh(deposit)
        return deposit

    @staticmethod
    def verify_security_deposit(
        db: Session,
        organization_id: uuid.UUID,
        deposit_id: uuid.UUID,
        request: SecurityDepositVerifyRequest,
        actor_id: Optional[uuid.UUID] = None,
    ) -> SecurityDeposit:
        deposit = db.execute(
            select(SecurityDeposit).where(
                SecurityDeposit.id == deposit_id,
                SecurityDeposit.organization_id == organization_id,
            )
        ).scalar_one_or_none()

        if not deposit:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Security deposit not found.",
            )

        prev_status = deposit.lien_status
        deposit.lien_status = request.lien_status
        if request.remarks:
            deposit.remarks = request.remarks

        db.add(
            AuditLog(
                organization_id=organization_id,
                user_id=actor_id,
                action="VERIFY_SECURITY_DEPOSIT_LIEN",
                entity_type="SecurityDeposit",
                entity_id=deposit.id,
                changes_json={
                    "previous_status": prev_status.value,
                    "new_status": request.lien_status.value,
                    "remarks": request.remarks,
                },
            )
        )
        db.commit()
        db.refresh(deposit)
        return deposit

    @staticmethod
    def list_security_deposits(
        db: Session,
        organization_id: uuid.UUID,
        group_id: Optional[uuid.UUID] = None,
        lien_status: Optional[LienStatus] = None,
    ) -> List[Dict[str, Any]]:
        query = (
            select(SecurityDeposit, ChitGroup, ChitScheme)
            .join(ChitGroup, SecurityDeposit.group_id == ChitGroup.id)
            .join(ChitScheme, ChitGroup.scheme_id == ChitScheme.id)
            .where(SecurityDeposit.organization_id == organization_id)
            .order_by(SecurityDeposit.created_at.desc())
        )
        if group_id:
            query = query.where(SecurityDeposit.group_id == group_id)
        if lien_status:
            query = query.where(SecurityDeposit.lien_status == lien_status)

        results = db.execute(query).all()
        output = []
        for dep, grp, sch in results:
            output.append({
                "id": dep.id,
                "organization_id": dep.organization_id,
                "group_id": dep.group_id,
                "group_code": grp.group_code,
                "group_name": f"{sch.name} ({grp.group_code})",
                "chit_value": sch.total_value,
                "deposit_type": dep.deposit_type,
                "bank_name": dep.bank_name,
                "account_or_fdr_number": dep.account_or_fdr_number,
                "amount": dep.amount,
                "deposit_date": dep.deposit_date,
                "maturity_date": dep.maturity_date,
                "registrar_order_reference": dep.registrar_order_reference,
                "lien_status": dep.lien_status,
                "remarks": dep.remarks,
                "created_at": dep.created_at,
                "updated_at": dep.updated_at,
            })
        return output

    # =========================================================================
    # REGISTRAR FILINGS & FORM XIV GENERATION
    # =========================================================================

    @staticmethod
    def generate_form_xiv_minutes_dict(
        db: Session,
        organization_id: uuid.UUID,
        auction_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Generates Form XIV (Minutes of Auction Proceedings) as mandated under
        Section 17 of the Chit Funds Act, 1982.
        """
        auction = db.execute(
            select(Auction)
            .options(
                selectinload(Auction.chit_group).selectinload(ChitGroup.scheme),
                selectinload(Auction.chit_group).selectinload(ChitGroup.branch),
                selectinload(Auction.winning_membership).selectinload(ChitMembership.user),
                selectinload(Auction.bids).selectinload(Bid.membership).selectinload(ChitMembership.user),
            )
            .where(Auction.id == auction_id)
        ).scalar_one_or_none()

        if not auction:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Auction round not found.",
            )

        if auction.chit_group.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to foreign organization auction is prohibited.",
            )

        if auction.status not in (AuctionStatus.CLOSED, AuctionStatus.FINALIZED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Form XIV Minutes can only be generated for concluded (CLOSED/FINALIZED) auction rounds.",
            )

        group = auction.chit_group
        scheme = group.scheme
        winning_mem = auction.winning_membership
        winner_user = winning_mem.user if winning_mem else None

        gross_chit_value = Decimal(str(scheme.total_value))
        winning_discount = Decimal(str(auction.winning_bid_discount))
        prized_amount = gross_chit_value - winning_discount

        # Filing deadline under Section 17 is generally within 2 months of auction date
        auction_date = auction.closed_at or auction.scheduled_at
        filing_deadline = (auction_date + timedelta(days=60)).date()

        # Format sorted bids
        sorted_bids = sorted(auction.bids, key=lambda b: (b.bid_discount_amount, -b.timestamp.timestamp()), reverse=True)
        bids_recorded = []
        for b in sorted_bids:
            bids_recorded.append({
                "ticket_number": b.membership.ticket_number,
                "subscriber_name": b.membership.user.full_name,
                "bid_discount": float(b.bid_discount_amount),
                "timestamp": b.timestamp.isoformat(),
            })

        return {
            "chit_group_code": group.group_code,
            "chit_group_name": f"{scheme.name} - Circle {group.group_code}",
            "prior_sanction_number": f"SANCTION-{group.group_code}-REG",
            "auction_id": auction.id,
            "auction_round": auction.month_number,
            "auction_date": auction_date,
            "chit_value": gross_chit_value,
            "winning_bid_discount": winning_discount,
            "foreman_commission": Decimal(str(auction.foreman_commission)),
            "dividend_total": Decimal(str(auction.total_dividend_pool)),
            "dividend_per_ticket": Decimal(str(auction.dividend_per_ticket)),
            "prized_amount": prized_amount,
            "prized_ticket_number": winning_mem.ticket_number if winning_mem else 0,
            "prized_subscriber_name": winner_user.full_name if winner_user else "Foreman Reserved Round",
            "prized_subscriber_phone": winner_user.phone if winner_user else "N/A",
            "prized_subscriber_address": "Registered Member on File",
            "registrar_office": f"Sub-Registrar of Chits, {group.branch.name}",
            "filing_deadline": filing_deadline,
            "bids_recorded": bids_recorded,
            "foreman_name": "Apex Chits Managing Director / Authorized Foreman",
        }

    @staticmethod
    def create_registrar_filing(
        db: Session,
        organization_id: uuid.UUID,
        data: RegistrarFilingCreate,
        actor_id: Optional[uuid.UUID] = None,
    ) -> RegistrarFiling:
        group = db.execute(
            select(ChitGroup).where(
                ChitGroup.id == data.group_id,
                ChitGroup.organization_id == organization_id,
            )
        ).scalar_one_or_none()

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chit group not found.",
            )

        # Unique filing reference check
        existing = db.execute(
            select(RegistrarFiling).where(
                RegistrarFiling.filing_reference_number == data.filing_reference_number
            )
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Filing reference '{data.filing_reference_number}' already exists.",
            )

        payload = None
        if data.form_type == FilingType.FORM_XIV_MINUTES and data.auction_id:
            try:
                form_xiv_data = ComplianceService.generate_form_xiv_minutes_dict(
                    db, organization_id, data.auction_id
                )
                # Convert Decimals/UUIDs to strings for JSONB
                payload = {
                    k: (str(v) if isinstance(v, (Decimal, uuid.UUID, date, datetime)) else v)
                    for k, v in form_xiv_data.items()
                }
            except Exception:
                payload = None

        filing = RegistrarFiling(
            organization_id=organization_id,
            group_id=data.group_id,
            auction_id=data.auction_id,
            form_type=data.form_type,
            filing_reference_number=data.filing_reference_number,
            filed_date=data.filed_date,
            registrar_office_name=data.registrar_office_name,
            acknowledgment_number=data.acknowledgment_number,
            status=FilingStatus.FILED if data.acknowledgment_number else FilingStatus.DRAFT,
            metadata_payload=payload,
            notes=data.notes,
        )
        db.add(filing)
        db.flush()

        db.add(
            AuditLog(
                organization_id=organization_id,
                user_id=actor_id,
                action="RECORD_REGISTRAR_FILING",
                entity_type="RegistrarFiling",
                entity_id=filing.id,
                changes_json={
                    "form_type": filing.form_type.value,
                    "ref": filing.filing_reference_number,
                    "office": filing.registrar_office_name,
                },
            )
        )
        db.commit()
        db.refresh(filing)
        return filing

    @staticmethod
    def update_registrar_filing(
        db: Session,
        organization_id: uuid.UUID,
        filing_id: uuid.UUID,
        update_data: RegistrarFilingUpdate,
        actor_id: Optional[uuid.UUID] = None,
    ) -> RegistrarFiling:
        filing = db.execute(
            select(RegistrarFiling).where(
                RegistrarFiling.id == filing_id,
                RegistrarFiling.organization_id == organization_id,
            )
        ).scalar_one_or_none()

        if not filing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registrar filing record not found.",
            )

        if update_data.acknowledgment_number is not None:
            filing.acknowledgment_number = update_data.acknowledgment_number
            filing.status = FilingStatus.ACKNOWLEDGED
        if update_data.status is not None:
            filing.status = update_data.status
        if update_data.notes is not None:
            filing.notes = update_data.notes

        db.add(
            AuditLog(
                organization_id=organization_id,
                user_id=actor_id,
                action="UPDATE_REGISTRAR_FILING",
                entity_type="RegistrarFiling",
                entity_id=filing.id,
                changes_json={
                    "status": filing.status.value,
                    "acknowledgment_number": filing.acknowledgment_number,
                },
            )
        )
        db.commit()
        db.refresh(filing)
        return filing

    @staticmethod
    def list_registrar_filings(
        db: Session,
        organization_id: uuid.UUID,
        group_id: Optional[uuid.UUID] = None,
        form_type: Optional[FilingType] = None,
        status_filter: Optional[FilingStatus] = None,
    ) -> List[Dict[str, Any]]:
        query = (
            select(RegistrarFiling, ChitGroup)
            .join(ChitGroup, RegistrarFiling.group_id == ChitGroup.id)
            .where(RegistrarFiling.organization_id == organization_id)
            .order_by(RegistrarFiling.filed_date.desc(), RegistrarFiling.created_at.desc())
        )
        if group_id:
            query = query.where(RegistrarFiling.group_id == group_id)
        if form_type:
            query = query.where(RegistrarFiling.form_type == form_type)
        if status_filter:
            query = query.where(RegistrarFiling.status == status_filter)

        results = db.execute(query).all()
        output = []
        for filing, grp in results:
            output.append({
                "id": filing.id,
                "organization_id": filing.organization_id,
                "group_id": filing.group_id,
                "group_code": grp.group_code,
                "auction_id": filing.auction_id,
                "form_type": filing.form_type,
                "filing_reference_number": filing.filing_reference_number,
                "filed_date": filing.filed_date,
                "registrar_office_name": filing.registrar_office_name,
                "acknowledgment_number": filing.acknowledgment_number,
                "status": filing.status,
                "metadata_payload": filing.metadata_payload,
                "notes": filing.notes,
                "created_at": filing.created_at,
                "updated_at": filing.updated_at,
            })
        return output

    # =========================================================================
    # CIRCLE BALANCE SHEET & FINANCIAL AUDIT RECONCILIATION
    # =========================================================================

    @staticmethod
    def get_circle_balance_sheet(
        db: Session,
        organization_id: uuid.UUID,
        group_id: uuid.UUID,
    ) -> Dict[str, Any]:
        group = db.execute(
            select(ChitGroup)
            .options(
                selectinload(ChitGroup.scheme),
                selectinload(ChitGroup.installments),
                selectinload(ChitGroup.auctions).selectinload(Auction.payout),
            )
            .where(
                ChitGroup.id == group_id,
                ChitGroup.organization_id == organization_id,
            )
        ).scalar_one_or_none()

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chit circle not found.",
            )

        scheme = group.scheme
        total_chit_value = Decimal(str(scheme.total_value))

        # Inflow: Installments collected & Late fees
        total_demanded = Decimal("0.00")
        total_collected = Decimal("0.00")
        total_penalties = Decimal("0.00")
        current_arrears = Decimal("0.00")

        for inst in group.installments:
            due = Decimal(str(inst.net_due_amount))
            paid = Decimal(str(inst.paid_amount))
            pen = Decimal(str(inst.penalty_amount))
            total_demanded += due
            total_collected += paid
            total_penalties += pen

            outstanding = (due + pen) - paid
            if outstanding > Decimal("0.00"):
                current_arrears += outstanding

        # Outflow: Payouts and Foreman charges
        total_prize_disbursed = Decimal("0.00")
        total_doc_fees = Decimal("0.00")
        total_dividends = Decimal("0.00")
        foreman_commission = Decimal("0.00")
        rounds_completed = 0

        for auc in group.auctions:
            if auc.status in (AuctionStatus.CLOSED, AuctionStatus.FINALIZED):
                rounds_completed += 1
                total_dividends += Decimal(str(auc.total_dividend_pool))
                foreman_commission += Decimal(str(auc.foreman_commission))

                if auc.payout and auc.payout.disbursement_status == PayoutStatus.DISBURSED:
                    total_prize_disbursed += Decimal(str(auc.payout.net_disbursed_amount))
                    total_doc_fees += Decimal(str(auc.payout.foreman_charges_deducted))

        total_gross_inflow = total_collected + total_penalties + total_doc_fees
        total_gross_outflow = total_prize_disbursed  # + defaulter refunds if any
        net_cash_pool_balance = total_gross_inflow - total_gross_outflow

        # Security Deposit pledged under Section 20
        pledged_res = db.execute(
            select(func.coalesce(func.sum(SecurityDeposit.amount), Decimal("0.00"))).where(
                SecurityDeposit.group_id == group_id,
                SecurityDeposit.lien_status == LienStatus.PLEDGED,
            )
        ).scalar()
        sec_20_lien_pledged = Decimal(str(pledged_res or "0.00"))

        return {
            "group_id": group.id,
            "group_code": group.group_code,
            "group_name": f"{scheme.name} ({group.group_code})",
            "total_chit_value": total_chit_value,
            "total_installments_demanded": total_demanded,
            "total_installments_collected": total_collected,
            "total_late_penalties_collected": total_penalties,
            "total_doc_fees_collected": total_doc_fees,
            "total_gross_inflow": total_gross_inflow,
            "total_prize_money_disbursed": total_prize_disbursed,
            "total_defaulter_refunds_paid": Decimal("0.00"),
            "total_gross_outflow": total_gross_outflow,
            "total_dividends_distributed": total_dividends,
            "foreman_commission_accrued": foreman_commission,
            "current_arrears_receivable": current_arrears,
            "sec_20_lien_pledged": sec_20_lien_pledged,
            "net_cash_pool_balance": net_cash_pool_balance,
            "rounds_completed": rounds_completed,
            "total_rounds": scheme.duration_months,
            "is_balanced": True,
        }

    # =========================================================================
    # DELINQUENCY AGING REPORT (30/60/90 DAYS NPA RADAR)
    # =========================================================================

    @staticmethod
    def get_delinquency_aging(
        db: Session,
        organization_id: uuid.UUID,
        group_id: uuid.UUID,
    ) -> Dict[str, Any]:
        group = db.execute(
            select(ChitGroup).where(
                ChitGroup.id == group_id,
                ChitGroup.organization_id == organization_id,
            )
        ).scalar_one_or_none()

        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chit group not found.",
            )

        # Get all unpaid / partially paid installments
        overdue_installments = db.execute(
            select(Installment, ChitMembership, User)
            .join(ChitMembership, Installment.chit_membership_id == ChitMembership.id)
            .join(User, ChitMembership.user_id == User.id)
            .where(
                Installment.chit_group_id == group_id,
                Installment.status.in_([
                    InstallmentStatus.UNPAID,
                    InstallmentStatus.PARTIALLY_PAID,
                    InstallmentStatus.OVERDUE,
                ]),
            )
            .order_by(Installment.due_date.asc())
        ).all()

        today = date.today()
        # Group by ticket
        ticket_map: Dict[uuid.UUID, Dict[str, Any]] = {}

        for inst, mem, usr in overdue_installments:
            due_amount = (Decimal(str(inst.net_due_amount)) + Decimal(str(inst.penalty_amount))) - Decimal(str(inst.paid_amount))
            if due_amount <= Decimal("0.00"):
                continue

            if mem.id not in ticket_map:
                ticket_map[mem.id] = {
                    "ticket_id": mem.id,
                    "ticket_number": mem.ticket_number,
                    "subscriber_name": usr.full_name,
                    "subscriber_phone": usr.phone,
                    "overdue_amount": Decimal("0.00"),
                    "unpaid_installments_count": 0,
                    "oldest_due_date": inst.due_date,
                    "days_overdue": max(0, (today - inst.due_date).days),
                }

            ticket_map[mem.id]["overdue_amount"] += due_amount
            ticket_map[mem.id]["unpaid_installments_count"] += 1
            if inst.due_date < ticket_map[mem.id]["oldest_due_date"]:
                ticket_map[mem.id]["oldest_due_date"] = inst.due_date
                ticket_map[mem.id]["days_overdue"] = max(0, (today - inst.due_date).days)

        current_dues = Decimal("0.00")   # 0-30 days
        dues_31_to_60 = Decimal("0.00")
        dues_61_to_90 = Decimal("0.00")
        npa_over_90 = Decimal("0.00")

        delinquent_list = []
        for t_info in ticket_map.values():
            days = t_info["days_overdue"]
            amt = t_info["overdue_amount"]
            if days <= 30:
                bucket = "0-30"
                current_dues += amt
            elif days <= 60:
                bucket = "31-60"
                dues_31_to_60 += amt
            elif days <= 90:
                bucket = "61-90"
                dues_61_to_90 += amt
            else:
                bucket = "90+"
                npa_over_90 += amt

            t_info["aging_bucket"] = bucket
            delinquent_list.append(t_info)

        total_delinquent = current_dues + dues_31_to_60 + dues_61_to_90 + npa_over_90

        return {
            "group_id": group.id,
            "group_code": group.group_code,
            "current_dues": current_dues,
            "dues_31_to_60": dues_31_to_60,
            "dues_61_to_90": dues_61_to_90,
            "npa_over_90": npa_over_90,
            "total_delinquent_amount": total_delinquent,
            "total_defaulters_count": len(delinquent_list),
            "delinquent_tickets": delinquent_list,
        }

    # =========================================================================
    # COMPLIANCE SYSTEM SUMMARY
    # =========================================================================

    @staticmethod
    def get_compliance_system_summary(
        db: Session,
        organization_id: Optional[uuid.UUID],
    ) -> Dict[str, Any]:
        # Total lien pledged
        pledged_q = select(func.coalesce(func.sum(SecurityDeposit.amount), Decimal("0.00"))).where(
            SecurityDeposit.lien_status == LienStatus.PLEDGED,
        )
        if organization_id:
            pledged_q = pledged_q.where(SecurityDeposit.organization_id == organization_id)
        pledged = db.execute(pledged_q).scalar()

        # Total filings & pending
        filings_q = select(func.count(RegistrarFiling.id))
        if organization_id:
            filings_q = filings_q.where(RegistrarFiling.organization_id == organization_id)
        total_filings = db.execute(filings_q).scalar() or 0

        pending_q = select(func.count(RegistrarFiling.id)).where(
            RegistrarFiling.status.in_([FilingStatus.DRAFT, FilingStatus.FILED]),
        )
        if organization_id:
            pending_q = pending_q.where(RegistrarFiling.organization_id == organization_id)
        pending_filings = db.execute(pending_q).scalar() or 0

        # Total prize disbursed across org
        prizes_q = (
            select(func.coalesce(func.sum(Payout.net_disbursed_amount), Decimal("0.00")))
            .join(Auction, Payout.auction_id == Auction.id)
            .join(ChitGroup, Auction.chit_group_id == ChitGroup.id)
            .where(Payout.disbursement_status == PayoutStatus.DISBURSED)
        )
        if organization_id:
            prizes_q = prizes_q.where(ChitGroup.organization_id == organization_id)
        prizes = db.execute(prizes_q).scalar()

        # Total active circles covered by pledged security
        covered_q = select(func.count(func.distinct(SecurityDeposit.group_id))).where(
            SecurityDeposit.lien_status == LienStatus.PLEDGED,
        )
        if organization_id:
            covered_q = covered_q.where(SecurityDeposit.organization_id == organization_id)
        covered_circles = db.execute(covered_q).scalar() or 0

        # Arrears
        unpaid_q = (
            select(
                func.coalesce(
                    func.sum(Installment.net_due_amount + Installment.penalty_amount - Installment.paid_amount),
                    Decimal("0.00"),
                )
            )
            .join(ChitGroup, Installment.chit_group_id == ChitGroup.id)
            .where(
                Installment.status.in_([InstallmentStatus.UNPAID, InstallmentStatus.PARTIALLY_PAID, InstallmentStatus.OVERDUE]),
            )
        )
        if organization_id:
            unpaid_q = unpaid_q.where(ChitGroup.organization_id == organization_id)
        unpaid_insts = db.execute(unpaid_q).scalar()

        return {
            "total_lien_pledged": Decimal(str(pledged or "0.00")),
            "active_circles_covered": covered_circles,
            "total_filings_count": total_filings,
            "pending_filings_count": pending_filings,
            "total_prize_disbursed": Decimal(str(prizes or "0.00")),
            "total_arrears_uncollected": Decimal(str(unpaid_insts or "0.00")),
        }
