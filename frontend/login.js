(() => {
  const API_BASE =
    (typeof window !== 'undefined' &&
      (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'))
      ? 'http://localhost:8000'
      : 'https://forma-dtzd.onrender.com';
  const SUPABASE_URL = 'https://uoptrdjzfzwnbwhkzhqi.supabase.co';
  const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVvcHRyZGp6Znp3bmJ3aGt6aHFpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU5MDk1MjcsImV4cCI6MjA5MTQ4NTUyN30.E5bVweqXIxH7oBR0YL-6bRxrzEOVWRmzj4gq9rWYMWg';

  let client = null;
  let mode = 'login';

  function setNote(msg, isError = false) {
    const el = document.getElementById('auth-page-note');
    if (!el) return;
    el.textContent = msg || '';
    el.classList.toggle('error', isError);
  }

  function setMode(next) {
    mode = next;
    const loginForm = document.getElementById('page-login-form');
    const registerForm = document.getElementById('page-register-form');
    const loginBtn = document.getElementById('page-login-btn');
    const registerBtn = document.getElementById('page-register-btn');
    const title = document.getElementById('auth-page-title');

    if (loginForm) loginForm.classList.toggle('hidden', mode !== 'login');
    if (registerForm) registerForm.classList.toggle('hidden', mode !== 'register');
    if (loginBtn) loginBtn.classList.toggle('active', mode === 'login');
    if (registerBtn) registerBtn.classList.toggle('active', mode === 'register');
    if (title) title.textContent = mode === 'register' ? 'Create your Forma account' : 'Log in to Forma';
    setNote('');
  }

  function getNextUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('next') || 'index.html#analyse';
  }

  function loadClient() {
    const supabaseUrl = String(SUPABASE_URL || '').trim();
    const supabaseAnonKey = String(SUPABASE_ANON_KEY || '').trim();
    if (!supabaseUrl || !supabaseAnonKey) throw new Error('Supabase auth config is missing in frontend');
    if (!window.supabase) throw new Error('Supabase browser SDK not loaded');
    client = window.supabase.createClient(supabaseUrl, supabaseAnonKey, {
      auth: { persistSession: true, autoRefreshToken: true },
    });
  }

  async function canUseBackendWithSession() {
    if (!client) return false;
    const { data } = await client.auth.getSession();
    const token = data?.session?.access_token;
    if (!token) return false;
    try {
      const res = await fetch(`${API_BASE}/history`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      return res.ok;
    } catch (_err) {
      return false;
    }
  }

  async function submitLogin(e) {
    e.preventDefault();
    if (!client) return;
    const email = document.getElementById('page-login-email')?.value || '';
    const password = document.getElementById('page-login-password')?.value || '';
    const { error } = await client.auth.signInWithPassword({ email, password });
    if (error) return setNote(error.message, true);
    const backendOk = await canUseBackendWithSession();
    if (!backendOk) {
      setNote('Logged in, but session could not be verified yet. Please try again.', true);
      await client.auth.signOut();
      return;
    }
    window.location.href = getNextUrl();
  }

  async function submitRegister(e) {
    e.preventDefault();
    if (!client) return;
    const email = document.getElementById('page-register-email')?.value || '';
    const password = document.getElementById('page-register-password')?.value || '';
    const { error } = await client.auth.signUp({ email, password });
    if (error) return setNote(error.message, true);
    setNote('Registered. You can now log in.');
    setMode('login');
  }

  async function init() {
    const params = new URLSearchParams(window.location.search);
    const initialMode = params.get('mode') === 'register' ? 'register' : 'login';
    setMode(initialMode);

    document.getElementById('page-login-btn')?.addEventListener('click', () => setMode('login'));
    document.getElementById('page-register-btn')?.addEventListener('click', () => setMode('register'));
    document.getElementById('page-login-form')?.addEventListener('submit', submitLogin);
    document.getElementById('page-register-form')?.addEventListener('submit', submitRegister);

    try {
      loadClient();
      const { data } = await client.auth.getSession();
      if (initialMode === 'login' && data?.session) {
        const backendOk = await canUseBackendWithSession();
        if (backendOk) {
          window.location.href = getNextUrl();
        } else {
          setNote('Session check failed. Please log in again.', true);
          await client.auth.signOut();
        }
      }
    } catch (err) {
      setNote(err.message || 'Auth setup failed', true);
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
