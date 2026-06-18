import { defineStore } from 'pinia'
import { ref } from 'vue'

const TOKEN_KEY = 'bid_token'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const loggedIn = ref(!!token.value)

  function setToken(t: string) {
    token.value = t
    loggedIn.value = true
    localStorage.setItem(TOKEN_KEY, t)
  }

  function logout() {
    token.value = ''
    loggedIn.value = false
    localStorage.removeItem(TOKEN_KEY)
  }

  return { token, loggedIn, setToken, logout }
})
