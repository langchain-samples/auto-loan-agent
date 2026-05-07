"""Mocked downstream API responses for the demo."""

DOCUMENT_REQUEST_RESPONSE = {
    "status": "ok",
    "ticket_id": "DOC-12345",
    "channel": "dealer_portal",
    "message": "Document request created. Dealer notified via portal.",
}

UNDERWRITER_NOTIFICATION_RESPONSE = {
    "status": "ok",
    "case_id": "UW-67890",
    "queue": "manual_review",
    "message": "Underwriter case opened. Routed to next available reviewer.",
}

DEALER_MESSAGE_RESPONSE = {
    "status": "ok",
    "message_id": "MSG-44455",
    "channel": "dealer_portal",
    "message": "Message delivered to dealer.",
}

def send_document_request():
    return DOCUMENT_REQUEST_RESPONSE

def notify_underwriter():
    return UNDERWRITER_NOTIFICATION_RESPONSE

def notify_dealer():
    return DEALER_MESSAGE_RESPONSE