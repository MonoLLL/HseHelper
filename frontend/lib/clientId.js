export function getClientId() {
  if (typeof window === "undefined") return null;

  let id = localStorage.getItem("client_id");
  if (!id) {
    // простой UUID без библиотек
    id = (crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`).toString();
    localStorage.setItem("client_id", id);
  }
  return id;
}
