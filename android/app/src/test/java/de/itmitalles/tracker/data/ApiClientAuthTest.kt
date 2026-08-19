package de.itmitalles.tracker.data

import kotlinx.coroutines.runBlocking
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Before
import org.junit.Test

class ApiClientAuthTest {
    private lateinit var server: MockWebServer

    @Before
    fun setUp() {
        ApiClient.resetForTest()
        server = MockWebServer()
        server.start()
    }

    @After
    fun tearDown() {
        server.shutdown()
        ApiClient.resetForTest()
    }

    @Test
    fun loginClientCannotPoisonAuthenticatedClientCache() = runBlocking {
        server.enqueue(
            MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody("""{"access_token":"synthetic-jwt","token_type":"bearer"}"""),
        )
        server.enqueue(
            MockResponse()
                .setHeader("Content-Type", "application/json")
                .setBody("[]"),
        )

        val baseUrl = server.url("/").toString()
        ApiClient.loginApi(baseUrl).login(LoginRequest("admin", "synthetic-password"))
        ApiClient.api(baseUrl) { "synthetic-jwt" }.listClients()

        assertNull(server.takeRequest().getHeader("Authorization"))
        assertEquals("Bearer synthetic-jwt", server.takeRequest().getHeader("Authorization"))
    }
}
