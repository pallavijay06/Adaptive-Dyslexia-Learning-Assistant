import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const ThemeContext = createContext(null);

function getSystemTheme() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function resolveTheme(mode) {
  return mode === 'dark' || mode === 'light' ? mode : getSystemTheme();
}

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    const storedTheme = window.localStorage.getItem('app-theme');
    return storedTheme || 'system';
  });
  const [resolvedTheme, setResolvedTheme] = useState(() => resolveTheme(window.localStorage.getItem('app-theme') || 'system'));

  useEffect(() => {
    const storedTheme = window.localStorage.getItem('app-theme');
    const currentTheme = storedTheme || 'system';
    const nextTheme = resolveTheme(currentTheme);
    setTheme(currentTheme);
    setResolvedTheme(nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
    document.documentElement.style.colorScheme = nextTheme;
  }, []);

  useEffect(() => {
    const nextTheme = resolveTheme(theme);
    setResolvedTheme(nextTheme);
    document.documentElement.setAttribute('data-theme', nextTheme);
    document.documentElement.style.colorScheme = nextTheme;
    if (theme !== 'system') {
      window.localStorage.setItem('app-theme', theme);
    } else {
      window.localStorage.removeItem('app-theme');
    }
  }, [theme]);

  useEffect(() => {
    if (theme !== 'system') {
      return undefined;
    }

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleChange = () => {
      const nextTheme = resolveTheme('system');
      setResolvedTheme(nextTheme);
      document.documentElement.setAttribute('data-theme', nextTheme);
      document.documentElement.style.colorScheme = nextTheme;
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [theme]);

  const value = useMemo(() => ({
    theme,
    resolvedTheme,
    setTheme,
    toggleTheme: () => setTheme((current) => (current === 'dark' ? 'light' : 'dark')),
  }), [resolvedTheme, theme]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  return useContext(ThemeContext);
}
