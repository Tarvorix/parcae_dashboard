from edgar import Company, set_identity
from typing import Optional
import pandas as pd

from backend.config import SEC_IDENTITY

# Required by SEC EDGAR before any request
set_identity(SEC_IDENTITY)

# ── GAAP concept fallback chains ────────────────────────────────────────────
# Companies use different GAAP concept names depending on industry and filing
# conventions.  We try multiple variants for each metric and use the first hit.

_REVENUE_CONCEPTS = [
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueServicesNet",
    "SalesRevenueGoodsNet",
    "InterestAndDividendIncomeOperating",
    "RegulatedAndUnregulatedOperatingRevenue",
    "ElectricUtilityRevenue",
    "HealthCareOrganizationRevenue",
    "RealEstateRevenueNet",
    "FinancialServicesRevenue",
    "BrokerageCommissionsRevenue",
    "OilAndGasRevenue",
    "RevenueFromRelatedParties",
    "TotalRevenuesAndOtherIncome",
    "NoninterestIncome",
    "RevenueNotFromContractWithCustomer",
    "Revenue",
]

_NET_INCOME_CONCEPTS = [
    "NetIncomeLoss",
    "NetIncomeLossAvailableToCommonStockholdersBasic",
    "ProfitLoss",
    "NetIncomeLossAttributableToParent",
    "IncomeLossFromContinuingOperations",
    "ComprehensiveIncomeNetOfTax",
    "IncomeLossFromContinuingOperationsIncludingPortionAttributableToNoncontrollingInterest",
]

_CFO_CONCEPTS = [
    "NetCashProvidedByUsedInOperatingActivities",
    "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
    "CashProvidedByUsedInOperatingActivitiesContinuingOperations",
    "NetCashProvidedByUsedInOperatingActivitiesOfContinuingOperations",
]

_CAPEX_CONCEPTS = [
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
    "PaymentsForCapitalImprovements",
    "CapitalExpendituresIncurredButNotYetPaid",
    "PaymentsToAcquireAndDevelopRealEstate",
    "PaymentsToAcquireMachineryAndEquipment",
    "PurchaseOfPropertyPlantAndEquipment",
    "PaymentsForProceedsFromProductiveAssets",
    "PaymentsToAcquireOtherPropertyPlantAndEquipment",
]

# Minimum number of annual filings needed for distribution fitting.
# 3 years provides enough data points (2+ growth rates) for bear/base/bull.
MIN_YEARS_REQUIRED = 3


def _lookup_concept(df: pd.DataFrame, concept_suffix: str, date_col: str) -> Optional[float]:
    """Look up a GAAP concept value from a Statement DataFrame."""
    full_concept = f"us-gaap_{concept_suffix}"
    mask = (df["concept"] == full_concept) & (df["dimension"] == False) & (df["abstract"] == False)
    rows = df.loc[mask, date_col]
    if rows.empty:
        return None
    val = rows.iloc[0]
    if pd.isna(val):
        return None
    return float(val)


def _lookup_first(df: pd.DataFrame, concepts: list[str], date_col: str) -> Optional[float]:
    """Try each concept in *concepts* and return the first non-None hit."""
    for concept in concepts:
        val = _lookup_concept(df, concept, date_col)
        if val is not None:
            return val
    return None


def get_10yr_financials(ticker: str) -> Optional[dict]:
    """
    Pull up to 10 years of annual financials from SEC EDGAR 10-K filings.
    Returns a dict with lists of annual values (oldest -> newest).
    Returns None if fewer than MIN_YEARS_REQUIRED years of usable data are
    found.
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
                tenk = filing.data_object()
                if tenk is None:
                    continue

                income_stmt = tenk.income_statement
                cf_stmt = tenk.cash_flow_statement
                if income_stmt is None or cf_stmt is None:
                    continue

                inc_df = income_stmt.to_dataframe()
                cf_df = cf_stmt.to_dataframe()

                # Find the primary period date column (first date column = most recent period)
                date_cols = [c for c in inc_df.columns if c[:2] == "20"]
                if not date_cols:
                    continue
                primary_date = date_cols[0]

                # Also need the same date column in cash flow
                cf_date_cols = [c for c in cf_df.columns if c[:2] == "20"]
                if not cf_date_cols:
                    continue
                cf_primary_date = cf_date_cols[0]

                # Revenue — try full fallback chain
                rev = _lookup_first(inc_df, _REVENUE_CONCEPTS, primary_date)

                # Net income — try full fallback chain
                ni = _lookup_first(inc_df, _NET_INCOME_CONCEPTS, primary_date)

                # Operating cash flow — try full fallback chain
                cfo = _lookup_first(cf_df, _CFO_CONCEPTS, cf_primary_date)

                # CapEx — try full fallback chain
                capex = _lookup_first(cf_df, _CAPEX_CONCEPTS, cf_primary_date)

                if rev and ni is not None and cfo is not None and capex is not None:
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

        if len(revenues) < MIN_YEARS_REQUIRED:
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
