package de.itmitalles.tracker.viewmodel

import android.app.Application
import android.content.Intent
import androidx.core.content.FileProvider
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import de.itmitalles.tracker.data.Invoice
import de.itmitalles.tracker.data.TrackerRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.io.File

class InvoicesViewModel(application: Application) : AndroidViewModel(application) {
    private val repo = TrackerRepository(application)

    private val _invoices = MutableStateFlow<List<Invoice>>(emptyList())
    val invoices: StateFlow<List<Invoice>> = _invoices.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            try {
                _invoices.value = repo.api().listInvoices()
            } catch (e: Exception) {
                _error.value = e.message
            }
        }
    }

    fun markPaid(id: Int) {
        viewModelScope.launch {
            try {
                repo.api().updateInvoiceStatus(id, mapOf("status" to "paid"))
                refresh()
            } catch (e: Exception) {
                _error.value = e.message
            }
        }
    }

    fun openPdf(invoice: Invoice) {
        viewModelScope.launch {
            try {
                val context = getApplication<android.app.Application>()
                val response = repo.api().downloadInvoicePdf(invoice.id)
                val body = response.body() ?: throw Exception("PDF leer")
                val dir = File(context.cacheDir, "pdfs").apply { mkdirs() }
                val file = File(dir, "${invoice.invoice_number}.pdf")
                file.outputStream().use { out -> body.byteStream().copyTo(out) }
                val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
                val intent = Intent(Intent.ACTION_VIEW).apply {
                    setDataAndType(uri, "application/pdf")
                    addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                }
                context.startActivity(intent)
            } catch (e: Exception) {
                _error.value = "PDF konnte nicht geöffnet werden: ${e.message}"
            }
        }
    }

    fun clearError() {
        _error.value = null
    }
}
