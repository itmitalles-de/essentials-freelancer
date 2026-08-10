package de.itmitalles.tracker.data

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Streaming

interface TrackerApi {
    @POST("api/auth/login")
    suspend fun login(@Body body: LoginRequest): TokenResponse

    @GET("api/clients")
    suspend fun listClients(): List<Client>

    @GET("api/time-entries")
    suspend fun listTimeEntries(
        @Query("client_id") clientId: Int? = null,
        @Query("billed") billed: Boolean? = null,
    ): List<TimeEntry>

    @GET("api/time-entries/running")
    suspend fun getRunning(): TimeEntry?

    @POST("api/time-entries")
    suspend fun createTimeEntry(@Body body: TimeEntryCreate): TimeEntry

    @POST("api/time-entries/start")
    suspend fun startTimer(@Body body: TimeEntryStart): TimeEntry

    @POST("api/time-entries/{id}/stop")
    suspend fun stopTimer(@Path("id") id: Int): TimeEntry

    @DELETE("api/time-entries/{id}")
    suspend fun deleteTimeEntry(@Path("id") id: Int): Response<Unit>

    @GET("api/invoices")
    suspend fun listInvoices(): List<Invoice>

    @Streaming
    @GET("api/invoices/{id}/pdf")
    suspend fun downloadInvoicePdf(@Path("id") id: Int): Response<okhttp3.ResponseBody>

    @PUT("api/invoices/{id}/status")
    suspend fun updateInvoiceStatus(@Path("id") id: Int, @Body body: Map<String, String>): Invoice
}
