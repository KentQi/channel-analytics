<template>
  <router-view />
</template>

<script setup>
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
@import './styles/responsive.css';

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  width: 100%;
  height: 100%;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

/* Global CSS Variables */
:root {
  --accent-primary: #00d9c0;
  --accent-secondary: #8b5cf6;
  --accent-tertiary: #06b6d4;
  --bg-dark: #0f1419;
  --bg-card: #1a1f2e;
  --bg-card-hover: #242b3d;
  --text-primary: #e2e8f0;
  --text-secondary: #94a3b8;
  --text-muted: #64748b;
  --border-subtle: rgba(255, 255, 255, 0.08);
  --border-glow: rgba(0, 217, 192, 0.3);
  --shadow-glow: 0 4px 20px rgba(0, 217, 192, 0.1);
  --shadow-card: 0 4px 24px rgba(0, 0, 0, 0.3);
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
}

::-webkit-scrollbar-thumb {
  background: rgba(0, 217, 192, 0.3);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 217, 192, 0.5);
}
</style>
