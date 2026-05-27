"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { EVENTS, track } from "@/lib/analytics";

export function UpgradeButton({
  plan = "pro",
  children = "升级到 Pro",
}: {
  plan?: "pro" | "pro_plus";
  children?: React.ReactNode;
}) {
  const [loading, setLoading] = useState(false);

  async function handleClick() {
    if (loading) return;
    setLoading(true);
    track(EVENTS.UPGRADE_CLICKED, { plan });
    try {
      const r = await fetch("/v1/billing/checkout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan }),
      });
      const data = await r.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        alert("升级暂时不可用,请稍后重试。");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <Button onClick={handleClick} disabled={loading}>
      {loading ? "正在跳转..." : children}
    </Button>
  );
}
