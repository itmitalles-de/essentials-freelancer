package de.itmitalles.tracker.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import de.itmitalles.tracker.data.ApiClient
import de.itmitalles.tracker.data.ThemeChoice
import de.itmitalles.tracker.data.TrackerRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

sealed interface AuthState {
    data object CheckingSession : AuthState
    data object LoggedOut : AuthState
    data object LoggedIn : AuthState
}

class AuthViewModel(application: Application) : AndroidViewModel(application) {
    private val repo = TrackerRepository(application)

    private val _authState = MutableStateFlow<AuthState>(AuthState.CheckingSession)
    val authState: StateFlow<AuthState> = _authState.asStateFlow()

    private val _loginError = MutableStateFlow<String?>(null)
    val loginError: StateFlow<String?> = _loginError.asStateFlow()

    private val _loading = MutableStateFlow(false)
    val loading: StateFlow<Boolean> = _loading.asStateFlow()

    val themeChoice: StateFlow<ThemeChoice> = repo.settings.themeChoice
        .stateIn(viewModelScope, SharingStarted.Eagerly, ThemeChoice.SYSTEM)

    init {
        ApiClient.onUnauthorized = { logout() }
        viewModelScope.launch {
            _authState.value = if (repo.isLoggedIn()) AuthState.LoggedIn else AuthState.LoggedOut
        }
    }

    suspend fun initialServerUrl(): String = repo.settings.serverUrl.first()

    fun login(serverUrl: String, username: String, password: String) {
        viewModelScope.launch {
            _loading.value = true
            _loginError.value = null
            try {
                repo.login(serverUrl, username, password)
                _authState.value = AuthState.LoggedIn
            } catch (e: Exception) {
                _loginError.value = "Anmeldung fehlgeschlagen: ${e.message ?: "Server nicht erreichbar"}"
            } finally {
                _loading.value = false
            }
        }
    }

    fun logout() {
        repo.logout()
        _authState.value = AuthState.LoggedOut
    }

    fun setThemeChoice(choice: ThemeChoice) {
        viewModelScope.launch { repo.settings.setThemeChoice(choice) }
    }
}
