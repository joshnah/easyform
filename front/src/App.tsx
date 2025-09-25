import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { useTranslation } from "react-i18next";
import "./localization/i18n";
import { updateAppLanguage } from "./helpers/language_helpers";
import { router } from "./routes/router";
import { RouterProvider } from "@tanstack/react-router";
import { BACKEND_URL } from "./const";

export default function App() {
  const { i18n } = useTranslation();
  const [isHealthy, setIsHealthy] = useState(false);

  useEffect(() => {
    // syncThemeWithLocal();
    updateAppLanguage(i18n);

    const checkHealth = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/health`);
        if (response.status === 200) {
          setIsHealthy(true);
        } else {
          throw new Error("Service not healthy");
        }
      } catch (error) {
        console.log("Health check failed, retrying...");
        setTimeout(checkHealth, 3000); // Retry after 1 second
      }
    };

    checkHealth();
  }, [i18n]);


  if (!isHealthy) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        background: 'linear-gradient(135deg, #f8fafc 0%, #e0e7ef 100%)',
        fontFamily: 'Segoe UI, Arial, sans-serif',
      }}>
        <div style={{
          width: 60,
          height: 60,
          border: '6px solid #cbd5e1',
          borderTop: '6px solid #2563eb',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite',
          marginBottom: 24,
        }}
        />
        <div style={{ fontSize: 22, color: '#334155', fontWeight: 500 }}>Trying to connect to backend...</div>
        <style>{`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  return <RouterProvider router={router} />;
}

const root = createRoot(document.getElementById("app")!);
root.render(
    <App />
);