"""
Tools for the Payment Agent (CredentialsProvider).

This file contains tools for creating PaymentMandates and simulating
the transfer of funds to verified African Tech Initiatives.
"""

from typing import Dict, Any
import logging
import hashlib
from datetime import datetime, timezone
from ap2.types.mandate import CartMandate, PaymentMandate, PaymentMandateContents
from ap2.types.payment_request import PaymentResponse

logger = logging.getLogger(__name__)


def _validate_cart_expiry(cart: CartMandate) -> tuple[bool, str]:
    """
    Validates that the CartMandate (Funding Contract) hasn't expired.
    
    This is a critical security check - expired offers should not be processed.
    
    Args:
        cart: The Pydantic CartMandate model to validate.
        
    Returns:
        (is_valid, error_message): Tuple indicating if cart is still valid.
    """
    try:
        expiry_str = cart.contents.cart_expiry
        # Handling ISO format quirks (Z vs +00:00)
        expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        if expiry_time < now:
            return False, f"Funding Offer (CartMandate) expired at {expiry_str}"
        
        time_remaining = expiry_time - now
        logger.info(f"CartMandate valid. Expires in {time_remaining.total_seconds():.0f} seconds")
        
        return True, ""
        
    except (ValueError, TypeError, AttributeError) as e:
        return False, f"Invalid cart_expiry format or structure: {e}"


def _create_payment_mandate(cart: CartMandate, consent_granted: bool) -> dict:
    """
    Creates a PaymentMandate using the official AP2 Pydantic models.
    
    It links to the CartMandate and includes user consent status to authorize
    the transfer of funds.
    """
    timestamp = datetime.now(timezone.utc)
    
    # Safely extract details from the validated CartMandate model
    cart_id = cart.contents.id
    merchant_name = cart.contents.merchant_name # This will contain the Initiative Name (e.g., She Code Africa)
    total_item = cart.contents.payment_request.details.total
    
    # Create the nested PaymentResponse model
    payment_response_model = PaymentResponse(
        request_id=cart_id,
        method_name="CARD",  # Simulated Card Payment
        details={"token": "simulated_funding_token_AFRICA_TECH"}
    )
    
    # Create the PaymentMandateContents model
    payment_mandate_contents_model = PaymentMandateContents(
        payment_mandate_id=f"payment_{hashlib.sha256(f'{cart_id}{timestamp.isoformat()}'.encode()).hexdigest()[:12]}",
        payment_details_id=cart_id,
        payment_details_total=total_item,
        payment_response=payment_response_model,
        merchant_agent=merchant_name,
        timestamp=timestamp.isoformat()
    )
    
    # Create the top-level PaymentMandate model
    payment_mandate_model = PaymentMandate(
        payment_mandate_contents=payment_mandate_contents_model
    )
    
    # Convert to dictionary for state storage
    final_dict = payment_mandate_model.model_dump(mode='json')
    
    # Add custom context fields for the demo state
    final_dict['payment_mandate_contents']['user_consent'] = consent_granted
    final_dict['payment_mandate_contents']['consent_timestamp'] = timestamp.isoformat() if consent_granted else None
    final_dict['agent_present'] = True
    
    return final_dict


async def create_payment_mandate(tool_context: Any) -> Dict[str, Any]:
    """
    Creates a PaymentMandate and simulates the secure transfer of funds.
    
    This tool reads the CartMandate from state, validates the contract,
    and executes the transaction logic.
    """
    logger.info("Tool called: Creating PaymentMandate and processing funding transfer")
    
    # 1. Read CartMandate dictionary from state
    cart_mandate_dict = tool_context.state.get("cart_mandate")
    if not cart_mandate_dict:
        logger.error("No CartMandate found in state")
        return { "status": "error", "message": "No CartMandate found. Merchant Agent must create the funding contract first." }
    
    # 2. Parse dictionary into a validated Pydantic model
    try:
        cart_model = CartMandate.model_validate(cart_mandate_dict)
    except Exception as e:
        logger.error(f"Could not validate CartMandate structure: {e}")
        return {"status": "error", "message": f"Invalid CartMandate structure: {e}"}
    
    # 3. Validate that the cart hasn't expired
    is_valid, error_message = _validate_cart_expiry(cart_model)
    if not is_valid:
        logger.error(f"CartMandate validation failed: {error_message}")
        return {"status": "error", "message": error_message}
    
    # 4. Safely extract data
    cart_id = cart_model.contents.id
    merchant_name = cart_model.contents.merchant_name
    amount_value = cart_model.contents.payment_request.details.total.amount.value
    currency = cart_model.contents.payment_request.details.total.amount.currency
    consent_granted = True  # Assume consent for this demo flow
    
    # 5. Create the spec-compliant PaymentMandate
    payment_mandate_dict = _create_payment_mandate(cart_model, consent_granted)
    
    # 6. Simulate payment processing (Funding Transfer)
    transaction_id = f"txn_{hashlib.sha256(f'{cart_id}{datetime.now(timezone.utc).isoformat()}'.encode()).hexdigest()[:16]}"
    payment_result = {
        "transaction_id": transaction_id,
        "status": "completed",
        "amount": amount_value,
        "currency": currency,
        "recipient": merchant_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "simulation": True
    }
    
    # 7. Write results to state
    tool_context.state["payment_mandate"] = payment_mandate_dict
    tool_context.state["payment_result"] = payment_result
    
    logger.info(f"Funding transfer processed successfully: {transaction_id}")
    
    return {
        "status": "success",
        # Updated success message to match the project tone
        "message": f"Funding of {currency} {amount_value:.2f} to {merchant_name} transferred successfully.",
        "transaction_id": transaction_id,
        "payment_mandate_id": payment_mandate_dict["payment_mandate_contents"]["payment_mandate_id"]
    }