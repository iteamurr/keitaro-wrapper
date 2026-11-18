from dataclasses import dataclass

from keitaro_wrapper.domain.common.errors import DomainError


@dataclass
class GatewayError(DomainError):
    uncertain: bool = False
