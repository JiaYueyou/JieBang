import { defineStore } from "pinia";
import { ref } from "vue";
import { loginApi, type LoginParams } from "@/api/auth";

export const useUserStore = defineStore(
  "user",
  () => {
    const token = ref("");
    const username = ref("");

    async function login(params: LoginParams) {
      const result = await loginApi(params);
      token.value = result.access_token;
      username.value = result.username;
      localStorage.setItem("token", result.access_token);
      localStorage.setItem("username", result.username);
    }

    function logout() {
      token.value = "";
      username.value = "";
      localStorage.removeItem("token");
      localStorage.removeItem("username");
    }

    function restore() {
      token.value = localStorage.getItem("token") || "";
      username.value = localStorage.getItem("username") || "";
    }

    return { token, username, login, logout, restore };
  },
);
