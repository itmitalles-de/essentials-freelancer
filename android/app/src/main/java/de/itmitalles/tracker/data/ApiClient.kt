package de.itmitalles.tracker.data

import kotlinx.serialization.json.Json
import okhttp3.Interceptor
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory

class UnauthorizedException : Exception("Nicht angemeldet")

object ApiClient {
    private var retrofit: Retrofit? = null
    private var currentBaseUrl: String? = null

    var onUnauthorized: (() -> Unit)? = null

    private val json = Json { ignoreUnknownKeys = true; explicitNulls = false }

    fun api(baseUrl: String, tokenProvider: () -> String?): TrackerApi {
        val normalized = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        if (retrofit == null || currentBaseUrl != normalized) {
            currentBaseUrl = normalized

            val authInterceptor = Interceptor { chain ->
                val token = tokenProvider()
                val request = chain.request().newBuilder().apply {
                    if (token != null) addHeader("Authorization", "Bearer $token")
                }.build()
                val response = chain.proceed(request)
                if (response.code == 401) {
                    onUnauthorized?.invoke()
                }
                response
            }

            val logging = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BASIC
            }

            val client = OkHttpClient.Builder()
                .addInterceptor(authInterceptor)
                .addInterceptor(logging)
                .build()

            retrofit = Retrofit.Builder()
                .baseUrl(normalized)
                .client(client)
                .addConverterFactory(
                    json.asConverterFactory("application/json".toMediaType())
                )
                .build()
        }
        return retrofit!!.create(TrackerApi::class.java)
    }
}
