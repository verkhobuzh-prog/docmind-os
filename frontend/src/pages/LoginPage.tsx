import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";

export function LoginPage() {
  const navigate = useNavigate();
  const signIn = useAuthStore((s) => s.signIn);
  const isLoading = useAuthStore((s) => s.isLoading);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await signIn(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign in failed");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-0 p-4 dark:bg-surface-dark-0">
      <Card className="w-full max-w-md">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Sign in</h1>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">DocMind OS — Enterprise Document AI</p>
        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <Input label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          {error && <p className="text-sm text-red-500">{error}</p>}
          <Button type="submit" className="w-full" loading={isLoading}>
            Sign in
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-gray-500 dark:text-gray-400">
          No account?{" "}
          <Link to="/register" className="text-brand-600 hover:underline dark:text-brand-400">
            Register
          </Link>
        </p>
      </Card>
    </div>
  );
}
