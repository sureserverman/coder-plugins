---
name: kotlin-compose-testing-patterns
description: >
  Testing patterns for Kotlin Android apps with Compose, Espresso, and MockWebServer.
  Use when writing Android tests, UI tests, instrumented tests, or setting up test infrastructure.
---

# Kotlin Compose Testing Patterns

Testing patterns for Jetpack Compose Android apps at unit, integration, and UI layers.

## Unit Tests (ViewModel)

```kotlin
@RunWith(AndroidJUnit4::class)
class LoginViewModelTest {
    @get:Rule
    val instantExecutorRule = InstantTaskExecutorRule()

    private lateinit var viewModel: LoginViewModel

    @Before
    fun setup() {
        viewModel = LoginViewModel(FakeAuthRepository())
    }

    @Test
    fun loginWithValidCredentials() {
        // Given
        val server = "https://matrix.example.com"
        val token = "valid_token"

        // When
        viewModel.login(server, token)

        // Then
        assertTrue(viewModel.isLoggedIn.value)
    }
}
```

Run: `./gradlew :feature:auth:testDebugUnitTest --tests LoginViewModelTest`

## Integration Tests (MockWebServer)

```kotlin
class AuthRepositoryTest {
    private lateinit var server: MockWebServer
    private lateinit var repository: AuthRepository

    @Before
    fun setup() {
        server = MockWebServer()
        server.start()

        val api = Retrofit.Builder()
            .baseUrl(server.url("/"))
            .addConverterFactory(Json.asConverterFactory("application/json".toMediaType()))
            .build()
            .create(SynapseApi::class.java)

        repository = AuthRepository(api)
    }

    @After
    fun teardown() {
        server.shutdown()
    }

    @Test
    fun wellKnownDiscovery() {
        server.enqueue(MockResponse()
            .setBody("""{"m.homeserver":{"base_url":"https://matrix.example.com"}}""")
            .setResponseCode(200))

        val result = runBlocking { repository.discover("example.com") }
        assertEquals("https://matrix.example.com", result.homeserverUrl)
    }
}
```

## Compose UI Tests

```kotlin
@RunWith(AndroidJUnit4::class)
class LoginScreenTest {
    @get:Rule
    val composeTestRule = createComposeRule()

    @Test
    fun loginFormDisplaysCorrectly() {
        composeTestRule.setContent {
            LoginScreen(onLogin = {})
        }

        composeTestRule
            .onNodeWithText("Server URL")
            .assertIsDisplayed()

        composeTestRule
            .onNodeWithTag("login_button")
            .assertIsEnabled()
    }

    @Test
    fun loginButtonTriggersCallback() {
        var loginCalled = false
        composeTestRule.setContent {
            LoginScreen(onLogin = { loginCalled = true })
        }

        composeTestRule
            .onNodeWithTag("server_url_field")
            .performTextInput("https://matrix.example.com")

        composeTestRule
            .onNodeWithTag("login_button")
            .performClick()

        composeTestRule.waitUntil(5000) { loginCalled }
        assertTrue(loginCalled)
    }
}
```

### Key Compose Test APIs
- `onNodeWithText("...")` — find by displayed text
- `onNodeWithTag("...")` — find by `Modifier.testTag("...")`
- `useUnmergedTree = true` — access semantic nodes inside merged composables
- `performClick()`, `performTextInput()` — interactions
- `waitUntil(timeoutMs) { condition }` — async UI updates
- `assertIsDisplayed()`, `assertIsEnabled()` — assertions

## Instrumented Tests (Espresso)

Run: `./gradlew :app:connectedAndroidTest`

Requires a connected device or running emulator.

## Test Output Filtering

```bash
./gradlew testDebugUnitTest --info 2>&1 | grep -E "PASSED|FAILED|ERROR"
```
