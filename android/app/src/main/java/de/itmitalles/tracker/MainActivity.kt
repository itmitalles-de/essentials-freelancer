package de.itmitalles.tracker

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import de.itmitalles.tracker.ui.TrackerApp
import de.itmitalles.tracker.ui.theme.TrackerTheme
import de.itmitalles.tracker.viewmodel.AuthViewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val authViewModel: AuthViewModel = viewModel()
            val themeChoice by authViewModel.themeChoice.collectAsState()

            TrackerTheme(themeChoice = themeChoice) {
                Surface(modifier = Modifier.fillMaxSize()) {
                    TrackerApp(authViewModel)
                }
            }
        }
    }
}
