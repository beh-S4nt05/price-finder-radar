import React, { createContext, useContext, useEffect, useState } from 'react';

export type ColdThemeMode = 'obsidian' | 'arctic';

interface ThemeContextValue {
  theme: ColdThemeMode;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: 'obsidian',
  toggleTheme: () => {},
});

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setTheme] = useState<ColdThemeMode>(() => {
    const saved = localStorage.getItem('iceberg_cold_theme');
    return saved === 'arctic' || saved === 'obsidian' ? saved : 'obsidian';
  });

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'obsidian') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('iceberg_cold_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'obsidian' ? 'arctic' : 'obsidian'));
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => useContext(ThemeContext);
