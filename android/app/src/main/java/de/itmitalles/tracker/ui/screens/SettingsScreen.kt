package de.itmitalles.tracker.ui.screens

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import de.itmitalles.tracker.data.ThemeChoice
import de.itmitalles.tracker.viewmodel.AuthViewModel

@Composable
fun SettingsScreen(viewModel: AuthViewModel) {
    val themeChoice by viewModel.themeChoice.collectAsState()

    Column(modifier = Modifier.padding(16.dp)) {
        Text("Farbschema", style = MaterialTheme.typography.titleMedium)
        Column(modifier = Modifier.selectableGroup()) {
            ThemeOption("System folgen", ThemeChoice.SYSTEM, themeChoice) { viewModel.setThemeChoice(it) }
            ThemeOption("Hell", ThemeChoice.LIGHT, themeChoice) { viewModel.setThemeChoice(it) }
            ThemeOption("Dunkel", ThemeChoice.DARK, themeChoice) { viewModel.setThemeChoice(it) }
        }

        androidx.compose.foundation.layout.Spacer(Modifier.padding(16.dp))
        Button(onClick = { viewModel.logout() }, modifier = Modifier.fillMaxWidth()) {
            Text("Abmelden")
        }
    }
}

@Composable
private fun ThemeOption(
    label: String,
    value: ThemeChoice,
    current: ThemeChoice,
    onSelect: (ThemeChoice) -> Unit,
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .selectable(selected = value == current, onClick = { onSelect(value) }),
    ) {
        RadioButton(selected = value == current, onClick = { onSelect(value) })
        Text(label, modifier = Modifier.padding(top = 12.dp))
    }
}
