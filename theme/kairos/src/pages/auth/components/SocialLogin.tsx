import GithubIcon from "@/assets/images/icons/github-icon.png";
import GoogleIcon from "@/assets/images/icons/google-icon.png";
import { Button } from "@/components/ui/button";
import { useIsSubmitting } from "@/context/isSubmittingContext";
import { signInWithGithub, signInWithGoogle } from "@/firebase";
import { Loader2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "react-toastify";

type Provider = "google" | "github" | null;

const SocialLogin = () => {
  const { isSubmitting, setIsSubmitting } = useIsSubmitting();
  const [activeProvider, setActiveProvider] = useState<Provider>(null);
  const navigate = useNavigate();

  const handleLogin = async (provider: Provider) => {
    try {
      setIsSubmitting(true);
      setActiveProvider(provider);

      const user =
        provider === "google"
          ? await signInWithGoogle()
          : await signInWithGithub();

      if (!user) return;

      toast.success(
        provider === "google"
          ? "Google login successful 🎉"
          : "Github login successful 🎉"
      );

      navigate("/dashboard");
    } catch {
      toast.error("Sign-in failed. Please try again.");
    } finally {
      setIsSubmitting(false);
      setActiveProvider(null);
    }
  };

  return (
    <div className="mt-8 flex items-center gap-3">
      {/* Google */}
      <Button
        variant="outline"
        className="font-semibold text-neutral-600 hover:text-neutral-600 dark:text-neutral-200 py-6 px-2 w-1/2 border border-neutral-600/50 rounded-xl text-sm flex items-center justify-center gap-3 line-height-1 hover:border-blue-400 hover:bg-primary/10 disabled:opacity-60"
        disabled={isSubmitting}
        onClick={() => handleLogin("google")}
      >
        {isSubmitting && activeProvider === "google" ? (
          <Loader2 className="animate-spin h-5 w-5" />
        ) : (
          <img src={GoogleIcon} alt="google" width={18} />
        )}
        Google
      </Button>

      {/* GitHub */}
      <Button
        variant="outline"
        className="font-semibold text-neutral-600 hover:text-neutral-600 dark:text-neutral-200 py-6 px-2 w-1/2 border border-neutral-600/50 rounded-xl text-sm flex items-center justify-center gap-3 line-height-1 hover:border-slate-400 hover:bg-slate-600/10 disabled:opacity-60"
        disabled={isSubmitting}
        onClick={() => handleLogin("github")}
      >
        {isSubmitting && activeProvider === "github" ? (
          <Loader2 className="animate-spin h-5 w-5" />
        ) : (
          <img src={GithubIcon} alt="github" width={18} />
        )}
        Github
      </Button>
    </div>
  );
};

export default SocialLogin;
