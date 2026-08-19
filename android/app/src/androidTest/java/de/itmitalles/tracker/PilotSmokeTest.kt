package de.itmitalles.tracker

import android.app.Activity
import android.app.Instrumentation.ActivityResult
import android.content.Intent
import androidx.compose.ui.test.assertCountEquals
import androidx.compose.ui.test.ExperimentalTestApi
import androidx.compose.ui.test.hasText
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performTextInput
import androidx.compose.ui.test.waitUntilAtLeastOneExists
import androidx.test.espresso.intent.Intents
import androidx.test.espresso.intent.Intents.intended
import androidx.test.espresso.intent.Intents.intending
import androidx.test.espresso.intent.matcher.IntentMatchers.hasAction
import androidx.test.platform.app.InstrumentationRegistry
import java.io.File
import org.junit.After
import org.junit.Before
import org.junit.Rule
import org.junit.Test

@OptIn(ExperimentalTestApi::class)
class PilotSmokeTest {
    @get:Rule
    val compose = createAndroidComposeRule<MainActivity>()

    private val arguments = InstrumentationRegistry.getArguments()
    private val serverUrl = arguments.getString("serverUrl") ?: "http://10.0.2.2:8080/"
    private val username = arguments.getString("username") ?: "admin"
    private val password = arguments.getString("password")
        ?: error("password instrumentation argument is required")

    @Before
    fun interceptExternalPdfViewer() {
        Intents.init()
        intending(hasAction(Intent.ACTION_VIEW)).respondWith(ActivityResult(Activity.RESULT_OK, null))
    }

    @After
    fun releaseIntents() {
        Intents.release()
    }

    @Test
    fun api35InternalPilotFlow() {
        compose.waitUntilAtLeastOneExists(hasText("Anmelden"), 15_000)
        compose.onNodeWithText("Server-URL (z.B. https://tracker.itmitalles.de)")
            .performTextInput(serverUrl)
        compose.onNodeWithText("Benutzername").performTextInput(username)
        compose.onNodeWithText("Passwort").performTextInput(password)
        compose.onNodeWithText("Anmelden").performClick()

        compose.waitUntilAtLeastOneExists(hasText("Zeit"), 20_000)
        compose.waitUntilAtLeastOneExists(hasText("TESTKUNDE", substring = true), 20_000)

        compose.onNodeWithText("Kunde wählen…").performClick()
        compose.onNodeWithText("TESTKUNDE").performClick()
        compose.onNodeWithText("Beschreibung").performTextInput("ANDROID STATE RESTORE")
        compose.activityRule.scenario.recreate()
        compose.waitUntilAtLeastOneExists(hasText("ANDROID STATE RESTORE"), 15_000)

        compose.onNodeWithText("Start").performClick()
        compose.waitUntilAtLeastOneExists(hasText("Stopp"), 20_000)
        compose.onNodeWithText("Stopp").performClick()
        compose.waitUntilAtLeastOneExists(hasText("Start"), 20_000)

        compose.onNodeWithText("Kunden").performClick()
        compose.waitUntilAtLeastOneExists(hasText("TESTKUNDE"), 20_000)
        compose.onAllNodesWithText("Speichern").assertCountEquals(0)

        compose.onNodeWithText("Rechnungen").performClick()
        compose.waitUntilAtLeastOneExists(hasText("TESTRECHNUNG", substring = true), 20_000)
        compose.onNodeWithText("sent").assertExists()
        compose.onNodeWithText("PDF öffnen").performClick()

        val context = InstrumentationRegistry.getInstrumentation().targetContext
        compose.waitUntil(20_000) {
            File(context.cacheDir, "pdfs").listFiles()?.any {
                it.name.startsWith("TESTRECHNUNG-") && it.readBytes().take(5).toByteArray().contentEquals("%PDF-".toByteArray())
            } == true
        }
        intended(hasAction(Intent.ACTION_VIEW))

        compose.onNodeWithText("Als bezahlt markieren").performClick()
        compose.waitUntilAtLeastOneExists(hasText("paid"), 20_000)
        compose.activityRule.scenario.recreate()
        compose.waitUntilAtLeastOneExists(hasText("TESTRECHNUNG", substring = true), 20_000)
        compose.onNodeWithText("paid").assertExists()
        compose.onAllNodesWithText("Als bezahlt markieren").assertCountEquals(0)
    }
}
