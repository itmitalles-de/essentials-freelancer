package de.itmitalles.tracker.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import de.itmitalles.tracker.viewmodel.TimeViewModel

@Composable
fun ClientsScreen(viewModel: TimeViewModel) {
    val clients by viewModel.clients.collectAsState()

    LazyColumn(modifier = Modifier.padding(16.dp)) {
        items(clients) { client ->
            Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                Column(modifier = Modifier.padding(12.dp)) {
                    Text(client.name, style = MaterialTheme.typography.titleMedium)
                    if (client.contact_person.isNotBlank()) {
                        Text(client.contact_person, style = MaterialTheme.typography.bodyMedium)
                    }
                    if (client.email.isNotBlank()) {
                        Text(client.email, style = MaterialTheme.typography.bodySmall)
                    }
                    Text(
                        "Satz: ${client.hourly_rate ?: "Standard"} €/h",
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
        }
    }
}
