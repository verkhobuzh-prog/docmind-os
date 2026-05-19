import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Card } from "@/components/ui/Card";

export function RegisterPage() {
  const navigate = useNavigate();
  const signUp = useAuthStore((s) => s.signUp);
  const isLoading = useAuthStore((s) => s.isLoading);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setMessage("");
    try {
      await signUp(email, password, name);
      setMessage("Check your email to confirm registration, or sign in if enabled.");
      setTimeout(() => navigate("/dashboard"), 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-surface-0 p-4 dark:bg-surface-dark-0">
      <Card className="w-full max-w-md">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Create account</h1>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Start using DocMind OS</p>
        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} required />
          <Input label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <Input
            label="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
          />
          {error && <p className="text-sm text-red-500">{error}</p>}
          {message && <p className="text-sm text-emerald-600 dark:text-emerald-400">{message}</p>}
          <Button type="submit" className="w-full" loading={isLoading}>
            Register
          </Button>
        </form>
        <p className="mt-4 text-center text-sm text-gray-500 dark:text-gray-400">
          Have an account?{" "}
          <Link to="/login" className="text-brand-600 hover:underline dark:text-brand-400">
            Sign in
          </Link>
        </p>
      </Card>
    </div>
  );
}
