package de.itmitalles.tracker.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import de.itmitalles.tracker.data.Invoice
import de.itmitalles.tracker.viewmodel.InvoicesViewModel

@Composable
fun InvoicesScreen(viewModel: InvoicesViewModel) {
    val invoices by viewModel.invoices.collectAsState()

    LazyColumn(modifier = Modifier.padding(16.dp)) {
        items(invoices) { invoice ->
            InvoiceRow(
                invoice,
                onOpenPdf = { viewModel.openPdf(invoice) },
                onMarkPaid = { viewModel.markPaid(invoice.id) },
            )
        }
    }
}

@Composable
private fun InvoiceRow(invoice: Invoice, onOpenPdf: () -> Unit, onMarkPaid: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(invoice.invoice_number, style = MaterialTheme.typography.titleMedium)
                AssistChip(onClick = {}, label = { Text(invoice.status) })
            }
            Text("${invoice.total} € — fällig ${invoice.due_date}", style = MaterialTheme.typography.bodyMedium)
            Row(modifier = Modifier.padding(top = 8.dp)) {
                Button(onClick = onOpenPdf) { Text("PDF öffnen") }
                if (invoice.status == "sent") {
                    androidx.compose.foundation.layout.Spacer(Modifier.padding(4.dp))
                    Button(onClick = onMarkPaid) { Text("Als bezahlt markieren") }
                }
            }
        }
    }
}
