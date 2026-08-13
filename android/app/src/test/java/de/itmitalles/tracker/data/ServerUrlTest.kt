package de.itmitalles.tracker.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class ServerUrlTest {
    @Test
    fun `normalizes whitespace and trailing slashes`() {
        assertEquals(
            "https://freelancer.example.invalid/",
            normalizeServerUrl("  https://freelancer.example.invalid///  "),
        )
        assertEquals(
            "http://localhost:8080/path/",
            normalizeServerUrl("http://localhost:8080/path"),
        )
    }

    @Test
    fun `rejects missing or unsafe schemes and credentials`() {
        listOf(
            "",
            "freelancer.example.invalid",
            "ftp://freelancer.example.invalid",
            "https://admin:secret@freelancer.example.invalid",
            "https://freelancer.example.invalid?token=secret",
            "https://freelancer.example.invalid/#fragment",
        ).forEach { value ->
            assertThrows(IllegalArgumentException::class.java) {
                normalizeServerUrl(value)
            }
        }
    }
}
