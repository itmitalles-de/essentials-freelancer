package de.itmitalles.tracker.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import de.itmitalles.tracker.data.ThemeChoice

private val LightColors = lightColorScheme(
    primary = Color(0xFF2F6FED),
    onPrimary = Color(0xFFFFFFFF),
    secondary = Color(0xFF5A6270),
    background = Color(0xFFF5F6F8),
    surface = Color(0xFFFFFFFF),
    error = Color(0xFFD64545),
)

private val DarkColors = darkColorScheme(
    primary = Color(0xFF5B8DFF),
    onPrimary = Color(0xFF0C1220),
    secondary = Color(0xFF9AA1AC),
    background = Color(0xFF14161A),
    surface = Color(0xFF1E2126),
    error = Color(0xFFEF6A6A),
)

@Composable
fun TrackerTheme(themeChoice: ThemeChoice, content: @Composable () -> Unit) {
    val systemDark = isSystemInDarkTheme()
    val useDark = when (themeChoice) {
        ThemeChoice.SYSTEM -> systemDark
        ThemeChoice.LIGHT -> false
        ThemeChoice.DARK -> true
    }

    val context = LocalContext.current
    val colorScheme = when {
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && useDark -> dynamicDarkColorScheme(context)
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && !useDark -> dynamicLightColorScheme(context)
        useDark -> DarkColors
        else -> LightColors
    }

    MaterialTheme(colorScheme = colorScheme, content = content)
}
