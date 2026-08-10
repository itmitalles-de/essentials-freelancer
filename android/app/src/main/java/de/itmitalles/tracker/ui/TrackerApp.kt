package de.itmitalles.tracker.ui

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.People
import androidx.compose.material.icons.filled.Receipt
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import de.itmitalles.tracker.ui.screens.ClientsScreen
import de.itmitalles.tracker.ui.screens.InvoicesScreen
import de.itmitalles.tracker.ui.screens.LoginScreen
import de.itmitalles.tracker.ui.screens.SettingsScreen
import de.itmitalles.tracker.ui.screens.TimeTrackingScreen
import de.itmitalles.tracker.viewmodel.AuthState
import de.itmitalles.tracker.viewmodel.AuthViewModel
import de.itmitalles.tracker.viewmodel.InvoicesViewModel
import de.itmitalles.tracker.viewmodel.TimeViewModel

private data class Tab(val route: String, val label: String, val icon: androidx.compose.ui.graphics.vector.ImageVector)

private val tabs = listOf(
    Tab("time", "Zeit", Icons.Filled.AccessTime),
    Tab("clients", "Kunden", Icons.Filled.People),
    Tab("invoices", "Rechnungen", Icons.Filled.Receipt),
    Tab("settings", "Einstellungen", Icons.Filled.Settings),
)

@Composable
fun TrackerApp(authViewModel: AuthViewModel) {
    val authState by authViewModel.authState.collectAsState()

    when (authState) {
        AuthState.CheckingSession -> {}
        AuthState.LoggedOut -> LoginScreen(authViewModel)
        AuthState.LoggedIn -> MainScaffold(authViewModel)
    }
}

@Composable
private fun MainScaffold(authViewModel: AuthViewModel) {
    val navController = rememberNavController()
    val timeViewModel: TimeViewModel = androidx.lifecycle.viewmodel.compose.viewModel()
    val invoicesViewModel: InvoicesViewModel = androidx.lifecycle.viewmodel.compose.viewModel()

    Scaffold(
        bottomBar = {
            NavigationBar {
                val navBackStackEntry by navController.currentBackStackEntryAsState()
                val currentDestination = navBackStackEntry?.destination

                tabs.forEach { tab ->
                    NavigationBarItem(
                        icon = { Icon(tab.icon, contentDescription = tab.label) },
                        label = { Text(tab.label) },
                        selected = currentDestination?.hierarchy?.any { it.route == tab.route } == true,
                        onClick = {
                            navController.navigate(tab.route) {
                                popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                    )
                }
            }
        }
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = "time",
            modifier = Modifier.padding(padding),
        ) {
            composable("time") { TimeTrackingScreen(timeViewModel) }
            composable("clients") { ClientsScreen(timeViewModel) }
            composable("invoices") { InvoicesScreen(invoicesViewModel) }
            composable("settings") { SettingsScreen(authViewModel) }
        }
    }
}
