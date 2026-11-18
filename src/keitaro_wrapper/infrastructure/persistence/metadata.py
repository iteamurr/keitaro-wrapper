from keitaro_wrapper.infrastructure.persistence.models.base import Base
from keitaro_wrapper.infrastructure.persistence.models.campaigns import CampaignRow
from keitaro_wrapper.infrastructure.persistence.models.integration import IntegrationRow
from keitaro_wrapper.infrastructure.persistence.models.offers import OfferRow
from keitaro_wrapper.infrastructure.persistence.models.operations import AttemptRow, OperationRow
from keitaro_wrapper.infrastructure.persistence.models.streams import StreamRow

MODEL_TYPES = (CampaignRow, StreamRow, OfferRow, OperationRow, AttemptRow, IntegrationRow)
metadata = Base.metadata
