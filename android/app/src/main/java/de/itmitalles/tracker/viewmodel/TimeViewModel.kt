package de.itmitalles.tracker.viewmodel

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import de.itmitalles.tracker.data.Client
import de.itmitalles.tracker.data.TimeEntry
import de.itmitalles.tracker.data.TimeEntryCreate
import de.itmitalles.tracker.data.TimeEntryStart
import de.itmitalles.tracker.data.TrackerRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class TimeViewModel(application: Application) : AndroidViewModel(application) {
    private val repo = TrackerRepository(application)

    private val _clients = MutableStateFlow<List<Client>>(emptyList())
    val clients: StateFlow<List<Client>> = _clients.asStateFlow()

    private val _entries = MutableStateFlow<List<TimeEntry>>(emptyList())
    val entries: StateFlow<List<TimeEntry>> = _entries.asStateFlow()

    private val _running = MutableStateFlow<TimeEntry?>(null)
    val running: StateFlow<TimeEntry?> = _running.asStateFlow()

    private val _elapsedSeconds = MutableStateFlow(0L)
    val elapsedSeconds: StateFlow<Long> = _elapsedSeconds.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    init {
        refresh()
        viewModelScope.launch {
            while (true) {
                val started = _running.value?.running_started_at
                if (started != null) {
                    _elapsedSeconds.value = secondsSince(started)
                }
                delay(1000)
            }
        }
    }

    fun refresh() {
        viewModelScope.launch {
            try {
                val api = repo.api()
                _clients.value = api.listClients()
                _entries.value = api.listTimeEntries()
                _running.value = api.getRunning()
            } catch (e: Exception) {
                _error.value = e.message
            }
        }
    }

    fun startTimer(clientId: Int, description: String) {
        viewModelScope.launch {
            try {
                _running.value = repo.api().startTimer(TimeEntryStart(clientId, description))
            } catch (e: Exception) {
                _error.value = e.message
            }
        }
    }

    fun stopTimer() {
        val id = _running.value?.id ?: return
        viewModelScope.launch {
            try {
                repo.api().stopTimer(id)
                _running.value = null
                refresh()
            } catch (e: Exception) {
                _error.value = e.message
            }
        }
    }

    fun addManualEntry(clientId: Int, date: String, description: String, hours: Double) {
        viewModelScope.launch {
            try {
                repo.api().createTimeEntry(
                    TimeEntryCreate(clientId, date, description, (hours * 60).toInt())
                )
                refresh()
            } catch (e: Exception) {
                _error.value = e.message
            }
        }
    }

    fun deleteEntry(id: Int) {
        viewModelScope.launch {
            try {
                repo.api().deleteTimeEntry(id)
                refresh()
            } catch (e: Exception) {
                _error.value = e.message
            }
        }
    }

    fun clearError() {
        _error.value = null
    }

    private fun secondsSince(isoLocal: String): Long {
        return try {
            val instant = java.time.LocalDateTime.parse(isoLocal.substringBefore("+"))
                .toInstant(java.time.ZoneOffset.UTC)
            java.time.Duration.between(instant, java.time.Instant.now()).seconds.coerceAtLeast(0)
        } catch (e: Exception) {
            0
        }
    }
}
