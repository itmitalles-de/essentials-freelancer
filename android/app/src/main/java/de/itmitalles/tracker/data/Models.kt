package de.itmitalles.tracker.data

import kotlinx.serialization.Serializable

@Serializable
data class LoginRequest(val username: String, val password: String)

@Serializable
data class TokenResponse(val access_token: String, val token_type: String = "bearer")

@Serializable
data class Client(
    val id: Int,
    val name: String,
    val contact_person: String = "",
    val address_line1: String = "",
    val address_line2: String = "",
    val zip_city: String = "",
    val email: String = "",
    val hourly_rate: String? = null,
    val notes: String = "",
    val active: Boolean = true,
)

@Serializable
data class TimeEntry(
    val id: Int,
    val client_id: Int,
    val date: String,
    val description: String = "",
    val duration_minutes: Int,
    val hourly_rate: String,
    val running_started_at: String? = null,
    val billed: Boolean,
    val invoice_id: Int? = null,
)

@Serializable
data class TimeEntryCreate(
    val client_id: Int,
    val date: String,
    val description: String = "",
    val duration_minutes: Int,
)

@Serializable
data class TimeEntryStart(val client_id: Int, val description: String = "")

@Serializable
data class InvoiceLineItem(
    val id: Int,
    val description: String,
    val quantity: String,
    val unit_price: String,
    val amount: String,
)

@Serializable
data class Invoice(
    val id: Int,
    val client_id: Int,
    val invoice_number: String,
    val issue_date: String,
    val due_date: String,
    val status: String,
    val total: String,
    val notes: String = "",
    val sent_at: String? = null,
    val paid_at: String? = null,
    val line_items: List<InvoiceLineItem> = emptyList(),
)
