import { defineStore } from "pinia";
import { ref } from "vue";
import { loginApi, type LoginParams } from "@/api/auth";

export const useUserStore = defineStore(
  "user",
  () => {
    const token = ref("");
    const username = ref("");
    const role = ref<"user" | "recruiter" | "admin">("user");

    async function login(params: LoginParams) {
      const result = await loginApi(params);
      token.value = result.access_token;
      username.value = result.username;
      role.value = result.role;
      localStorage.setItem("token", result.access_token);
      localStorage.setItem("username", result.username);
      localStorage.setItem("role", result.role);
    }

    function logout() {
      token.value = "";
      username.value = "";
      role.value = "user";
      localStorage.removeItem("token");
      localStorage.removeItem("username");
      localStorage.removeItem("role");
    }

    function restore() {
      token.value = localStorage.getItem("token") || "";
      username.value = localStorage.getItem("username") || "";
      const storedRole = localStorage.getItem("role");
      role.value = storedRole === "admin" || storedRole === "recruiter" ? storedRole : "user";
    }

    return { token, username, role, login, logout, restore };
  },
);
