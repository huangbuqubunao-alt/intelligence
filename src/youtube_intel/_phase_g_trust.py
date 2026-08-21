"""Runtime-only trust primitives for Phase G trusted registration.

These objects are created inside ``RuntimeOperations`` composition and are
not exposed through any public API.  They exist so that
``_RegistrationAuthority`` can be constructed only with a runtime-minted
issuance capability, without exposing an ``issue yourself`` method or a
mutable boolean flag.
"""

from __future__ import annotations


class _RuntimeIssuanceCapability:
    """Opaque capability minted once per RuntimeOperations instance.

    Normal instantiation is rejected.  ``RuntimeOperations`` creates the
    single valid instance via ``object.__new__`` and passes it to
    ``_RegistrationAuthority`` during composition.  Because the capability
    itself has no public constructor and carries no caller-supplied
    marker, a caller cannot derive or forge a valid authority by importing
    private names.
    """

    __slots__ = ()

    def __new__(cls) -> "_RuntimeIssuanceCapability":
        msg = (
            "_RuntimeIssuanceCapability cannot be instantiated directly; "
            "it is created only by RuntimeOperations composition"
        )
        raise RuntimeError(msg)
