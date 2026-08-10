package de.itmitalles.tracker.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.dataStore by preferencesDataStore(name = "tracker_settings")

enum class ThemeChoice { SYSTEM, LIGHT, DARK }

class AppSettings(private val context: Context) {
    private val serverUrlKey = stringPreferencesKey("server_url")
    private val themeKey = stringPreferencesKey("theme_choice")

    val serverUrl: Flow<String> =
        context.dataStore.data.map { it[serverUrlKey] ?: "" }

    val themeChoice: Flow<ThemeChoice> =
        context.dataStore.data.map {
            runCatching { ThemeChoice.valueOf(it[themeKey] ?: "SYSTEM") }.getOrDefault(ThemeChoice.SYSTEM)
        }

    suspend fun setServerUrl(url: String) {
        context.dataStore.edit { it[serverUrlKey] = url }
    }

    suspend fun setThemeChoice(choice: ThemeChoice) {
        context.dataStore.edit { it[themeKey] = choice.name }
    }

    suspend fun currentServerUrl(): String = serverUrl.first()

    private val encryptedPrefs by lazy {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            "tracker_secure_prefs",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    fun getToken(): String? = encryptedPrefs.getString("jwt_token", null)

    fun setToken(token: String?) {
        encryptedPrefs.edit().apply {
            if (token == null) remove("jwt_token") else putString("jwt_token", token)
        }.apply()
    }
}
