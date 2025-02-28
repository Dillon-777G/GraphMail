# Python standard library imports
import logging
from typing import Any, Dict, List

# Third party imports
from kiota_abstractions.api_error import APIError
from msgraph.generated.models.exchange_id_format import ExchangeIdFormat
from msgraph.generated.users.item.translate_exchange_ids.translate_exchange_ids_post_request_body import (
    TranslateExchangeIdsPostRequestBody,
)

# Application imports
from app.error_handling.exceptions.id_translation_exception import IdTranslationException
from app.service.graph.graph_authentication_service import Graph


class GraphIDTranslator:
    def __init__(self, graph: Graph):
        self.logger = logging.getLogger(__name__)
        self.graph = graph


    async def translate_ids(self, input_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Translate regular IDs to immutable IDs for emails using the SDK's built-in translate_exchange_ids method.

        Args:
            input_ids (List[str]): List of input IDs to translate.

        Returns:
            List[Dict[str, Any]]: Translated IDs with source and target mapping.
        """
        self.logger.info("Starting ID translation service for %d input IDs", len(input_ids))
        try:
            if not input_ids:
                raise IdTranslationException(
                    detail="No input IDs to translate", status_code=400
                )

            await self.graph.ensure_authenticated()
            request_body = TranslateExchangeIdsPostRequestBody(
                input_ids=input_ids,
                source_id_type=ExchangeIdFormat.RestId,
                target_id_type=ExchangeIdFormat.RestImmutableEntryId,
            )

            result = await self.graph.client.me.translate_exchange_ids.post(request_body)
            if not result or not result.value:
                self.logger.error("No results returned from translation service")
                raise IdTranslationException(
                    detail="No results returned from translation service",
                    source_ids=input_ids,
                    status_code=500
                )

            self.logger.info("Translation service completed successfully for %d input IDs", len(input_ids))
            return [
                {"source_id": item.source_id, "target_id": item.target_id}
                for item in result.value
            ]

        except APIError as e:
            self.logger.error("API Error in translate_ids: %s", str(e))
            raise e
        except IdTranslationException as e:
            self.logger.error("Error translating IDs: %s", e)
            raise
        except Exception as e:
            self.logger.error("Error translating IDs: %s", e)
            raise IdTranslationException(
                detail=f"Failed to translate IDs: {str(e)}",
                source_ids=input_ids,
                status_code=500,
            ) from e