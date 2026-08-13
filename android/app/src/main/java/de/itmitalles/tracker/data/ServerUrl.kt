package de.itmitalles.tracker.data

import java.net.URI

fun normalizeServerUrl(raw: String): String {
    val trimmed = raw.trim().trimEnd('/')
    require(trimmed.isNotEmpty()) { "Server-URL fehlt" }
    val uri = runCatching { URI(trimmed) }
        .getOrElse { throw IllegalArgumentException("Server-URL ist ungültig") }
    require(uri.scheme == "https" || uri.scheme == "http") {
        "Server-URL muss mit http:// oder https:// beginnen"
    }
    require(!uri.host.isNullOrBlank() && uri.userInfo == null && uri.fragment == null && uri.query == null) {
        "Server-URL ist ungültig"
    }
    return "$trimmed/"
}
