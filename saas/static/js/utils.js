// js/utils.js - Utility helpers shared across modules

export function togglePasswordVisibility(id) {
  const input = document.getElementById(id);
  input.type = input.type === 'password' ? 'text' : 'password';
}

export function fillPrompt(text) {
  const input = document.getElementById('main-prompt-input');
  input.value = text;
  input.dispatchEvent(new Event('input'));
  input.focus();
}

export function debounce(func, wait) {
  let timeout;
  return function (...args) {
    clearTimeout(timeout);
    timeout = setTimeout(() => func.apply(this, args), wait);
  };
}
