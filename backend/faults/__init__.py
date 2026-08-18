"""faults — Smart Fault Injection catalog + injector."""
from faults.fault_catalog import Fault, FaultType, FAULT_CATALOG
from faults.smart_fault_injector import SmartFaultInjector, FaultEvent

__all__ = [
    "Fault",
    "FaultType",
    "FAULT_CATALOG",
    "SmartFaultInjector",
    "FaultEvent",
]