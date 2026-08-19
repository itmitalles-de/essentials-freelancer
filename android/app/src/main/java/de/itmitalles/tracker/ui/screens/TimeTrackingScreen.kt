package de.itmitalles.tracker.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import de.itmitalles.tracker.data.Client
import de.itmitalles.tracker.data.TimeEntry
import de.itmitalles.tracker.viewmodel.TimeViewModel

@Composable
fun TimeTrackingScreen(viewModel: TimeViewModel) {
    val clients by viewModel.clients.collectAsState()
    val entries by viewModel.entries.collectAsState()
    val running by viewModel.running.collectAsState()
    val elapsed by viewModel.elapsedSeconds.collectAsState()
    var showManualDialog by rememberSaveable { mutableStateOf(false) }
    var selectedClientId by rememberSaveable { mutableStateOf<Int?>(null) }
    var timerDescription by rememberSaveable { mutableStateOf("") }

    Scaffold(
        floatingActionButton = {
            FloatingActionButton(onClick = { showManualDialog = true }) {
                Icon(Icons.Filled.Add, contentDescription = "Manueller Eintrag")
            }
        }
    ) { padding ->
        Column(modifier = Modifier.padding(padding).padding(16.dp)) {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    if (running != null) {
                        val hh = elapsed / 3600
                        val mm = (elapsed % 3600) / 60
                        val ss = elapsed % 60
                        Text(
                            clientName(clients, running!!.client_id) +
                                " — " + "%02d:%02d:%02d".format(hh, mm, ss),
                            style = MaterialTheme.typography.titleLarge,
                        )
                        if (running!!.description.isNotBlank()) {
                            Text(running!!.description, style = MaterialTheme.typography.bodyMedium)
                        }
                        Button(onClick = { viewModel.stopTimer() }, modifier = Modifier.fillMaxWidth()) {
                            Text("Stopp")
                        }
                    } else {
                        ClientDropdown(clients, selectedClientId) { selectedClientId = it }
                        OutlinedTextField(
                            value = timerDescription,
                            onValueChange = { timerDescription = it },
                            label = { Text("Beschreibung") },
                            modifier = Modifier.fillMaxWidth(),
                        )
                        Button(
                            onClick = {
                                selectedClientId?.let { viewModel.startTimer(it, timerDescription) }
                                timerDescription = ""
                            },
                            enabled = selectedClientId != null,
                            modifier = Modifier.fillMaxWidth(),
                        ) {
                            Text("Start")
                        }
                    }
                }
            }

            Text(
                "Einträge",
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.padding(top = 16.dp, bottom = 8.dp),
            )

            LazyColumn {
                items(entries) { entry ->
                    TimeEntryRow(entry, clientName(clients, entry.client_id)) {
                        viewModel.deleteEntry(entry.id)
                    }
                }
            }
        }
    }

    if (showManualDialog) {
        ManualEntryDialog(
            clients = clients,
            onDismiss = { showManualDialog = false },
            onSave = { clientId, date, description, hours ->
                viewModel.addManualEntry(clientId, date, description, hours)
                showManualDialog = false
            },
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun ClientDropdown(clients: List<Client>, selectedId: Int?, onSelect: (Int) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    val selectedName = clients.find { it.id == selectedId }?.name ?: "Kunde wählen…"

    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }) {
        OutlinedTextField(
            value = selectedName,
            onValueChange = {},
            readOnly = true,
            label = { Text("Kunde") },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            modifier = Modifier
                .menuAnchor(MenuAnchorType.PrimaryNotEditable)
                .fillMaxWidth()
                .padding(bottom = 8.dp),
        )
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            clients.forEach { client ->
                DropdownMenuItem(
                    text = { Text(client.name) },
                    onClick = {
                        onSelect(client.id)
                        expanded = false
                    },
                )
            }
        }
    }
}

@Composable
private fun TimeEntryRow(entry: TimeEntry, clientName: String, onDelete: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Row(
            modifier = Modifier.padding(12.dp).fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Column {
                Text("$clientName — ${entry.date}", style = MaterialTheme.typography.bodyLarge)
                Text(entry.description, style = MaterialTheme.typography.bodySmall)
                Text(
                    "%.2f h · %s €/h".format(entry.duration_minutes / 60.0, entry.hourly_rate),
                    style = MaterialTheme.typography.bodySmall,
                )
                Text(
                    if (entry.billed) "abgerechnet" else "offen",
                    style = MaterialTheme.typography.labelSmall,
                )
            }
            if (!entry.billed) {
                Button(onClick = onDelete) { Text("Löschen") }
            }
        }
    }
}

@Composable
private fun ManualEntryDialog(
    clients: List<Client>,
    onDismiss: () -> Unit,
    onSave: (Int, String, String, Double) -> Unit,
) {
    var selectedClientId by rememberSaveable { mutableStateOf<Int?>(null) }
    var date by rememberSaveable { mutableStateOf(java.time.LocalDate.now().toString()) }
    var description by rememberSaveable { mutableStateOf("") }
    var hours by rememberSaveable { mutableStateOf("") }

    androidx.compose.material3.AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Manueller Eintrag") },
        text = {
            Column {
                ClientDropdown(clients, selectedClientId) { selectedClientId = it }
                OutlinedTextField(value = date, onValueChange = { date = it }, label = { Text("Datum (JJJJ-MM-TT)") })
                OutlinedTextField(value = description, onValueChange = { description = it }, label = { Text("Beschreibung") })
                OutlinedTextField(value = hours, onValueChange = { hours = it }, label = { Text("Stunden") })
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val h = hours.toDoubleOrNull()
                    if (selectedClientId != null && h != null) {
                        onSave(selectedClientId!!, date, description, h)
                    }
                },
            ) { Text("Speichern") }
        },
        dismissButton = {
            Button(onClick = onDismiss) { Text("Abbrechen") }
        },
    )
}

private fun clientName(clients: List<Client>, id: Int): String =
    clients.find { it.id == id }?.name ?: "?"
