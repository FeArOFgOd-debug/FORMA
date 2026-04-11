(() => {
  const SUPABASE_URL = 'https://uoptrdjzfzwnbwhkzhqi.supabase.co';
  const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVvcHRyZGp6Znp3bmJ3aGt6aHFpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU5MDk1MjcsImV4cCI6MjA5MTQ4NTUyN30.E5bVweqXIxH7oBR0YL-6bRxrzEOVWRmzj4gq9rWYMWg';
  const LOGIN_QUERY_KEY = 'auth';

  const state = {
    client: null,
    session: null,
    initialized: false,
    supabaseUrl: SUPABASE_URL,
    supabaseAnonKey: SUPABASE_ANON_KEY,
  };

  function getClient() {
    if (state.client) return state.client;
    if (!window.supabase || !state.supabaseUrl || !state.supabaseAnonKey) return null;
    state.client = window.supabase.createClient(state.supabaseUrl, state.supabaseAnonKey, {
      auth: { persistSession: true, autoRefreshToken: true },
    });
    return state.client;
  }

  function ensureModal() {
    const root = document.getElementById('auth-modal-root');
    if (!root || root.innerHTML.trim()) return;
    root.innerHTML = `
      <div class="auth-modal hidden" id="auth-modal">
        <div class="auth-backdrop" id="auth-backdrop"></div>
        <div class="auth-card">
          <div class="auth-head">
            <h3 id="auth-title">Log in</h3>
            <button class="auth-close" id="auth-close" type="button">x</button>
          </div>
          <p class="auth-note" id="auth-note"></p>
          <form id="auth-login-form" class="auth-form">
            <input id="auth-login-email" type="email" placeholder="Email" required />
            <input id="auth-login-password" type="password" placeholder="Password" required />
            <button type="submit">Log in</button>
          </form>
          <form id="auth-signup-form" class="auth-form hidden">
            <input id="auth-signup-email" type="email" placeholder="Email" required />
            <input id="auth-signup-password" type="password" placeholder="Password (min 6 chars)" minlength="6" required />
            <button type="submit">Create account</button>
          </form>
          <form id="auth-reset-form" class="auth-form hidden">
            <input id="auth-reset-email" type="email" placeholder="Email" required />
            <button type="submit">Send reset link</button>
          </form>
          <div class="auth-actions">
            <button type="button" class="auth-switch" id="auth-show-login">Log in</button>
            <button type="button" class="auth-switch" id="auth-show-signup">Sign up</button>
            <button type="button" class="auth-switch" id="auth-show-reset">Forgot password</button>
          </div>
        </div>
      </div>
    `;
  }

  function setNote(message, isError) {
    const note = document.getElementById('auth-note');
    if (!note) return;
    note.textContent = message || '';
    note.classList.toggle('error', Boolean(isError));
  }

  function showAuth(mode = 'login') {
    ensureModal();
    const modal = document.getElementById('auth-modal');
    if (!modal) return;
    modal.classList.remove('hidden');
    ['login', 'signup', 'reset'].forEach((m) => {
      const form = document.getElementById(`auth-${m}-form`);
      if (form) form.classList.toggle('hidden', mode !== m);
    });
    const title = document.getElementById('auth-title');
    if (title) title.textContent = mode === 'signup' ? 'Create account' : (mode === 'reset' ? 'Reset password' : 'Log in');
    setNote('', false);
  }

  function hideAuth() {
    const modal = document.getElementById('auth-modal');
    if (modal) modal.classList.add('hidden');
  }

  function renderNavAuth(loggedIn) {
    const loginBtn = document.getElementById('auth-login-btn');
    const registerBtn = document.getElementById('auth-register-btn');
    const logoutBtn = document.getElementById('auth-logout-btn');
    const userLabel = document.getElementById('auth-user-label');
    const user = state.session?.user || null;
    const rawName = String(
      user?.user_metadata?.full_name ||
      user?.user_metadata?.name ||
      user?.email ||
      ''
    ).trim();
    const displayName = rawName.includes('@') ? rawName.split('@')[0] : rawName;

    if (loginBtn) loginBtn.classList.toggle('hidden', Boolean(loggedIn));
    if (registerBtn) registerBtn.classList.toggle('hidden', Boolean(loggedIn));
    if (logoutBtn) logoutBtn.classList.toggle('hidden', !loggedIn);
    if (userLabel) {
      userLabel.classList.toggle('hidden', !loggedIn);
      userLabel.textContent = loggedIn ? displayName : '';
      userLabel.title = user?.email || '';
    }
  }

  function updateAuthButtons() {
    renderNavAuth(Boolean(state.session?.user));
  }

  async function refreshSession() {
    const client = getClient();
    if (!client) {
      state.session = null;
      updateAuthButtons();
      return null;
    }
    const { data } = await client.auth.getSession();
    state.session = data?.session || null;
    updateAuthButtons();
    return state.session;
  }

  async function getAccessToken() {
    const session = state.session || await refreshSession();
    return session?.access_token || null;
  }

  function getUser() {
    return state.session?.user || null;
  }

  function openAuthFromQuery() {
    const params = new URLSearchParams(window.location.search);
    if (params.get(LOGIN_QUERY_KEY) === 'login') {
      const next = encodeURIComponent(window.location.href);
      window.location.href = `login.html?mode=login&next=${next}`;
    }
  }

  function redirectToLogin() {
    const next = encodeURIComponent(window.location.href);
    window.location.href = `login.html?mode=login&next=${next}`;
  }

  function redirectToRegister() {
    const next = encodeURIComponent(window.location.href);
    window.location.href = `login.html?mode=register&next=${next}`;
  }

  async function requireUser() {
    const session = state.session || await refreshSession();
    return Boolean(session?.user);
  }

  async function signOut() {
    const client = getClient();
    if (!client) return;
    await client.auth.signOut();
    state.session = null;
    updateAuthButtons();
  }

  async function initAuthUI() {
    if (state.initialized) return;
    state.initialized = true;
    ensureModal();
    const client = getClient();

    const loginBtn = document.getElementById('auth-login-btn');
    const registerBtn = document.getElementById('auth-register-btn');
    const logoutBtn = document.getElementById('auth-logout-btn');
    const closeBtn = document.getElementById('auth-close');
    const backdrop = document.getElementById('auth-backdrop');
    const loginForm = document.getElementById('auth-login-form');
    const signupForm = document.getElementById('auth-signup-form');
    const resetForm = document.getElementById('auth-reset-form');

    if (loginBtn) loginBtn.addEventListener('click', redirectToLogin);
    if (registerBtn) registerBtn.addEventListener('click', redirectToRegister);
    if (logoutBtn) {
      logoutBtn.addEventListener('click', async () => {
        const originalText = logoutBtn.textContent || 'Logout';
        logoutBtn.disabled = true;
        logoutBtn.textContent = 'Logging out...';
        try {
          await signOut();
          await refreshSession();
          renderNavAuth(false);
          window.location.href = 'index.html';
        } catch (_err) {
          setNote('Logout failed. Please try again.', true);
          logoutBtn.disabled = false;
          logoutBtn.textContent = originalText;
        }
      });
    }
    if (closeBtn) closeBtn.addEventListener('click', hideAuth);
    if (backdrop) backdrop.addEventListener('click', hideAuth);

    const showLogin = document.getElementById('auth-show-login');
    const showSignup = document.getElementById('auth-show-signup');
    const showReset = document.getElementById('auth-show-reset');
    if (showLogin) showLogin.addEventListener('click', redirectToLogin);
    if (showSignup) showSignup.addEventListener('click', redirectToRegister);
    if (showReset) showReset.addEventListener('click', redirectToLogin);

    if (loginForm) {
      loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const liveClient = getClient();
        if (!liveClient) {
          setNote('Auth service is not configured yet.', true);
          return;
        }
        const email = document.getElementById('auth-login-email')?.value || '';
        const password = document.getElementById('auth-login-password')?.value || '';
        const { error } = await liveClient.auth.signInWithPassword({ email, password });
        if (error) return setNote(error.message, true);
        await refreshSession();
        hideAuth();
      });
    }

    if (signupForm) {
      signupForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const liveClient = getClient();
        if (!liveClient) {
          setNote('Auth service is not configured yet.', true);
          return;
        }
        const email = document.getElementById('auth-signup-email')?.value || '';
        const password = document.getElementById('auth-signup-password')?.value || '';
        const { error } = await liveClient.auth.signUp({ email, password });
        if (error) return setNote(error.message, true);
        setNote('Signup successful. Check your email if confirmation is required.', false);
      });
    }

    if (resetForm) {
      resetForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const liveClient = getClient();
        if (!liveClient) {
          setNote('Auth service is not configured yet.', true);
          return;
        }
        const email = document.getElementById('auth-reset-email')?.value || '';
        const redirectTo = `${window.location.origin}${window.location.pathname}`;
        const { error } = await liveClient.auth.resetPasswordForEmail(email, { redirectTo });
        if (error) return setNote(error.message, true);
        setNote('Reset link sent. Check your email.', false);
      });
    }

    if (client) {
      await refreshSession();
      client.auth.onAuthStateChange((_event, session) => {
        state.session = session || null;
        renderNavAuth(Boolean(state.session?.user));
      });
    } else {
      renderNavAuth(false);
    }
    openAuthFromQuery();
  }

  window.Auth = {
    initAuthUI,
    getAccessToken,
    requireUser,
    getUser,
    signOut,
    showAuth,
    redirectToLogin,
    redirectToRegister,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      initAuthUI();
    });
  } else {
    initAuthUI();
  }
})();
