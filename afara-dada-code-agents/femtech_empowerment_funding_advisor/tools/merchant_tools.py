"""
Tools for the MerchantAgent.

This file contains tools for creating W3C-compliant CartMandates
and simulating merchant signatures for Verified African Tech Initiatives.
"""

from typing import Dict, Any
import logging
import hashlib
import json
from datetime import datetime, timezone, timedelta
from ap2.types.mandate import IntentMandate, CartMandate, CartContents
from ap2.types.payment_request import (
    PaymentRequest,
    PaymentMethodData,
    PaymentDetailsInit,
    PaymentItem,
    PaymentCurrencyAmount,
    PaymentOptions,
)

logger = logging.getLogger(__name__)


def _validate_intent_expiry(intent_expiry_str: str) -> tuple[bool, str]:
    """
    Validates that the IntentMandate hasn't expired.
    This ensures the funding offer is still valid before processing.
    
    Args:
        intent_expiry_str: The ISO 8601 timestamp string from the IntentMandate.
        
    Returns:
        (is_valid, error_message)
    """
    try:
        # Handling ISO format quirks (Z vs +00:00)
        expiry_time = datetime.fromisoformat(intent_expiry_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        if expiry_time < now:
            return False, f"Funding Intent expired at {intent_expiry_str}"
        
        time_remaining = expiry_time - now
        logger.info(f"IntentMandate valid. Expires in {time_remaining.total_seconds():.0f} seconds")
        
        return True, ""
        
    except (ValueError, TypeError) as e:
        return False, f"Invalid intent_expiry format: {e}"


def _generate_merchant_signature(cart_contents: CartContents) -> str:
    """
    Generates a simulated merchant signature for the CartMandate contents.
    
    This represents the 'Binding Commitment' from the organization to use
    the funds as specified in the offer.
    """
    # Dump Pydantic model to dict
    cart_contents_dict = cart_contents.model_dump(mode='json')
    
    # Create canonical JSON string
    cart_json = json.dumps(cart_contents_dict, sort_keys=True, separators=(',', ':'))
    
    # Generate SHA-256 hash
    cart_hash = hashlib.sha256(cart_json.encode('utf-8')).hexdigest()
    
    # Create signature format
    signature = f"SIG_{cart_hash[:16]}"
    
    logger.info(f"Generated organization signature: {signature}")
    return signature


async def create_cart_mandate(tool_context: Any) -> Dict[str, Any]:
    """
    Creates a W3C PaymentRequest-compliant CartMandate from the IntentMandate.
    
    This tool transforms the user's 'desire to fund' into a 'contractual offer'
    from the selected African Tech Organization.
    
    Returns:
        Dictionary containing status and the created CartMandate.
    """
    logger.info("Tool called: Creating CartMandate from Funding Intent")
    
    # 1. Read IntentMandate from state
    intent_mandate_dict = tool_context.state.get("intent_mandate")
    if not intent_mandate_dict:
        logger.error("No IntentMandate found in state")
        return {
            "status": "error",
            "message": "No IntentMandate found. Finding Agent must create intent first."
        }
    
    # 2. Parse dictionary into validated Pydantic model
    try:
        intent_mandate_model = IntentMandate.model_validate(intent_mandate_dict)
    except Exception as e:
        logger.error(f"Could not validate IntentMandate structure: {e}")
        return {"status": "error", "message": f"Invalid IntentMandate structure: {e}"}
    
    # 3. Validate Expiry (Security Check)
    is_valid, error_message = _validate_intent_expiry(intent_mandate_model.intent_expiry)
    if not is_valid:
        logger.error(f"IntentMandate validation failed: {error_message}")
        return {"status": "error", "message": error_message}
    
    # 4. Extract Data
    # Note: We use the first merchant in the list, defaulting to 'Unknown Initiative' if empty
    org_name = intent_mandate_model.merchants[0] if intent_mandate_model.merchants else "Unknown Initiative"
    amount = intent_mandate_dict.get("amount", 0.0)
    
    # 5. Build CartMandate Models
    timestamp = datetime.now(timezone.utc)
    # Unique Cart ID generation
    cart_id = f"cart_{hashlib.sha256(f'{org_name}{timestamp.isoformat()}'.encode()).hexdigest()[:12]}"
    cart_expiry = timestamp + timedelta(minutes=15)
    
    payment_request_model = PaymentRequest(
        method_data=[PaymentMethodData(
            supported_methods="CARD",
            data={
                "supported_networks": ["visa", "mastercard"], 
                "supported_types": ["debit", "credit"]
            }
        )],
        details=PaymentDetailsInit(
            id=f"order_{cart_id}",
            display_items=[PaymentItem(
                label=f"Tech Empowerment Funding: {org_name}",
                amount=PaymentCurrencyAmount(currency="USD", value=amount)
            )],
            total=PaymentItem(
                label="Total Contribution",
                amount=PaymentCurrencyAmount(currency="USD", value=amount)
            )
        ),
        options=PaymentOptions(request_shipping=False)
    )
    
    cart_contents_model = CartContents(
        id=cart_id,
        cart_expiry=cart_expiry.isoformat(),
        merchant_name=org_name,
        user_cart_confirmation_required=False,
        payment_request=payment_request_model
    )
    
    # 6. Generate Signature (The Proof)
    signature = _generate_merchant_signature(cart_contents_model)
    
    # 7. Create Final CartMandate
    cart_mandate_model = CartMandate(
        contents=cart_contents_model,
        merchant_authorization=signature
    )
    
    # 8. Store in State
    cart_mandate_dict = cart_mandate_model.model_dump(mode='json')
    cart_mandate_dict["timestamp"] = timestamp.isoformat()
    
    tool_context.state["cart_mandate"] = cart_mandate_dict
    
    logger.info(f"CartMandate created successfully: {cart_id}")
    
    return {
        "status": "success",
        "message": f"Created signed CartMandate {cart_id} for ${amount:.2f} funding to {org_name}",
        "cart_id": cart_id,
        "cart_expiry": cart_expiry.isoformat(),
        "signature": signature
    }