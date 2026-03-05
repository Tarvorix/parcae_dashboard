from edgar import Company, set_identity
from typing import Optional
import pandas as pd

from backend.config import SEC_IDENTITY

# Required by SEC EDGAR before any request
set_identity(SEC_IDENTITY)


def get_10yr_financials(ticker: str) -> Optional[dict]:
    """
    Pull up to 10 years of annual financials from SEC EDGAR 10-K filings.
    Returns a dict with lists of annual values (oldest → newest).
    Returns None if fewer than 5 years of usable data are found.
    """
    try:
        company = Company(ticker)
        filings = company.get_filings(form="10-K").head(12)

        revenues: list[float] = []
        net_incomes: list[float] = []
        fcfs: list[float] = []
        margins: list[float] = []
        capex_list: list[float] = []

        for filing in filings:
            try:
                financials = filing.financials
                income = financials.income_statement
                cashflow = financials.cash_flow_statement

                rev = (
                    income.get("Revenues")
                    or income.get("RevenueFromContractWithCustomerExcludingAssessedTax")
                )
                ni = income.get("NetIncomeLoss")
                cfo = cashflow.get("NetCashProvidedByUsedInOperatingActivities")
                capex = cashflow.get("PaymentsToAcquirePropertyPlantAndEquipment")

                if rev and ni and cfo and capex:
                    rev_f = float(rev)
                    ni_f = float(ni)
                    cfo_f = float(cfo)
                    capex_f = abs(float(capex))
                    fcf = cfo_f - capex_f

                    revenues.append(rev_f)
                    net_incomes.append(ni_f)
                    fcfs.append(fcf)
                    margins.append(ni_f / rev_f if rev_f > 0 else 0.0)
                    capex_list.append(capex_f)
            except Exception:
                continue

        if len(revenues) < 5:
            return None  # Not enough history for reliable distributions

        # Filings come newest-first; reverse to chronological order
        return {
            "revenues": list(reversed(revenues)),
            "net_incomes": list(reversed(net_incomes)),
            "fcfs": list(reversed(fcfs)),
            "margins": list(reversed(margins)),
            "capex": list(reversed(capex_list)),
        }

    except Exception:
        return None
