import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
});

// Inject auth token
api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("trackme_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Handle 401 — redirect to login (skip auth endpoints to avoid redirect loops)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || "";
    const isAuthEndpoint = url.includes("/auth/");
    if (error.response?.status === 401 && typeof window !== "undefined" && !isAuthEndpoint) {
      localStorage.removeItem("trackme_token");
      localStorage.removeItem("trackme_refresh_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;

// Auth
export const authGoogle = (code: string, redirectUri: string) =>
  api.post("/auth/google", { code, redirect_uri: redirectUri });

export const refreshToken = (token: string) =>
  api.post("/auth/refresh", { refresh_token: token });

export const getMe = () => api.get("/auth/me");

// Dashboard
export const getDashboardSummary = () => api.get("/dashboard/summary");
export const getHoldingsSummary = (params?: Record<string, string>) =>
  api.get("/dashboard/holdings", { params });
export const getTopMovers = () => api.get("/dashboard/top-movers");

// Portfolio
export const getPortfolios = () => api.get("/portfolio/");
export const createPortfolio = (name: string) =>
  api.post("/portfolio/", { name });
export const getPortfolioHoldings = (id: string, params?: Record<string, string>) =>
  api.get(`/portfolio/${id}/holdings`, { params });

// Transactions
export const getTransactions = (params?: Record<string, string | number>) =>
  api.get("/transactions/", { params });

// Alerts
export const getAlerts = () => api.get("/alerts/");
export const createAlert = (data: Record<string, unknown>) =>
  api.post("/alerts/", data);
export const deleteAlert = (id: string) => api.delete(`/alerts/${id}`);
export const toggleAlert = (id: string) => api.patch(`/alerts/${id}/toggle`);
export const getAlertHistory = () => api.get("/alerts/history");

// AI Chat
export const sendChatMessage = (message: string, conversationId?: string) =>
  api.post("/chat/", { message, conversation_id: conversationId });
export const getConversations = () => api.get("/chat/conversations");
export const getConversationMessages = (id: string) =>
  api.get(`/chat/conversations/${id}/messages`);
export const deleteConversation = (id: string) =>
  api.delete(`/chat/conversations/${id}`);

// Subscription
export const getSubscription = () => api.get("/subscription/");
export const getPlans = () => api.get("/subscription/plans");
export const createCheckout = (plan: string, billing?: string) =>
  api.post(`/subscription/checkout?plan=${plan}&billing=${billing || "monthly"}`);
export const verifyPayment = (data: Record<string, string>) =>
  api.post("/subscription/verify", null, { params: data });

// Import
export const uploadCAS = (file: File, password: string) => {
  const form = new FormData();
  form.append("file", file);
  form.append("password", password);
  return api.post("/import/cas-upload", form);
};
export const addManualTransaction = (data: Record<string, unknown>) =>
  api.post("/import/manual", data);
export const getImportHistory = () => api.get("/import/history");
export const triggerEmailScan = () => api.post("/import/email/scan-now");

// Notifications
export const getNotifications = () => api.get("/notifications/");
export const getUnreadCount = () => api.get("/notifications/unread-count");
export const markNotificationRead = (id: string) => api.patch(`/notifications/${id}/read`);
export const markAllNotificationsRead = () => api.post("/notifications/mark-all-read");

// Asset Search
export const searchAssets = (q: string) => api.get("/assets/search", { params: { q } });

// MF Aggregator (PAN + OTP)
export const startMFConnect = (pan: string) =>
  api.post("/mf/connect/start", { pan });
export const verifyMFConnect = (sessionId: string, otp: string) =>
  api.post("/mf/connect/verify", { session_id: sessionId, otp });
export const syncMF = () => api.post("/mf/sync");
export const getMFConnection = () => api.get("/mf/connection");

// Insurance
export const getInsurancePolicies = () => api.get("/insurance/");
export const createInsurancePolicy = (data: Record<string, unknown>) =>
  api.post("/insurance/", data);
export const updateInsurancePolicy = (id: string, data: Record<string, unknown>) =>
  api.patch(`/insurance/${id}`, data);
export const deleteInsurancePolicy = (id: string) => api.delete(`/insurance/${id}`);

// Settings
export const getEmailConfig = () => api.get("/settings/email");
export const saveEmailConfig = (data: Record<string, unknown>) =>
  api.post("/settings/email", data);
export const getWhatsAppConfig = () => api.get("/settings/whatsapp");
export const saveWhatsAppConfig = (data: Record<string, unknown>) =>
  api.post("/settings/whatsapp", data);
export const updateProfile = (data: Record<string, unknown>) =>
  api.patch("/settings/profile", data);

// Gmail Integration
export const getEmailOAuthUrl = () => api.get("/settings/email/oauth/authorize");
export const saveEmailOAuthCallback = (code: string, redirectUri: string) =>
  api.post("/settings/email/oauth/callback", { code, redirect_uri: redirectUri });
export const saveCASPassword = (password: string) =>
  api.post("/settings/email/cas-password", { password });
