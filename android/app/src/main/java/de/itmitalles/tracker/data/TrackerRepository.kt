package de.itmitalles.tracker.data

import android.content.Context
import kotlinx.coroutines.flow.first

class TrackerRepository(context: Context) {
    val settings = AppSettings(context.applicationContext)

    suspend fun api(): TrackerApi {
        val baseUrl = settings.serverUrl.first()
        return ApiClient.api(baseUrl) { settings.getToken() }
    }

    suspend fun login(serverUrl: String, username: String, password: String) {
        settings.setServerUrl(serverUrl)
        val api = ApiClient.api(serverUrl) { null }
        val token = api.login(LoginRequest(username, password)).access_token
        settings.setToken(token)
    }

    fun logout() {
        settings.setToken(null)
    }

    fun isLoggedIn(): Boolean = settings.getToken() != null
}
