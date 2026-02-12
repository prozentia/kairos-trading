import AuthImage from "@/assets/images/auth/auth-img.png";
import ThemeLogo from "@/components/shared/ThemeLogo";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { useIsSubmitting } from "@/context/isSubmittingContext";
import { loginWithEmailAndPassword } from "@/firebase";
import { Eye, EyeOff, Loader2, Lock, Mail } from 'lucide-react';
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from 'react-toastify';
import SocialLogin from "../components/SocialLogin";

import {
    Field,
    FieldError,
    FieldGroup
} from "@/components/ui/field";
import { cn } from "@/lib/utils";
import { zodResolver } from "@hookform/resolvers/zod";
import { Controller, useForm } from "react-hook-form";
import * as z from "zod";


const formSchema = z.object({
    email: z.string().email("Enter a valid email address."),
    password: z
        .string()
        .min(6, "Password must be at least 6 characters.")
        .max(20, "Password must be at most 10 characters."),
});


const Login = () => {
    const navigate = useNavigate();
    const { isSubmitting, setIsSubmitting } = useIsSubmitting();
    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            email: "",
            password: "",
        },
    });

    const handleLogin = async (data: z.infer<typeof formSchema>) => {
        setIsSubmitting(true);
        setIsLoading(true);

        try {
            const user = await loginWithEmailAndPassword(data.email, data.password);

            if (!user) return;
            toast.success(`Login in successful.`);
            if (user) {
                navigate("/dashboard");
            };
        } catch (error) {
            toast.error(`${error}`);
        } finally {
            setIsSubmitting(false);
            setIsLoading(false);
            form.reset();
        }
    }

    return (
        <section className="bg-white dark:bg-slate-900 lg:flex flex-wrap min-h-[100vh]">
            <div className="lg:w-1/2 lg:block hidden">
                <div className="flex items-center flex-col h-full justify-center">
                    <img src={AuthImage} alt="Image" />
                </div>
            </div>
            <div className="lg:w-1/2 py-8 px-6 flex flex-col justify-center">
                <div className="lg:max-w-[464px] mx-auto w-full">
                    <div>
                        <Link to="/dashboard" className="mb-2.5 max-w-[290px] inline-block">
                            <ThemeLogo />
                        </Link>
                        <h4 className="mb-3">Sign In to your Account</h4>
                        <p className="mb-8 text-secondary-light text-lg">Welcome back! please enter your detail</p>
                    </div>

                    <form action="#" onSubmit={form.handleSubmit(handleLogin)}>
                        <FieldGroup className="mb-4">
                            <Controller
                                name="email"
                                control={form.control}
                                render={({ field, fieldState }) => (
                                    <Field data-invalid={fieldState.invalid} className={cn('gap-1')}>
                                        <div className="icon-field relative">
                                            <Mail className="absolute start-5 top-1/2 transform -translate-y-1/2 w-5 h-5 text-neutral-700 dark:text-neutral-200" />
                                            <Input
                                                {...field}
                                                type="email"
                                                aria-invalid={fieldState.invalid}
                                                disabled={isSubmitting}
                                                placeholder="Email"
                                                name="email"
                                                autoComplete="off"
                                                className="ps-13 pe-12 h-14 rounded-xl bg-neutral-100 dark:bg-slate-800 border border-neutral-300 dark:border-slate-700 focus:border-primary dark:focus:border-primary focus-visible:border-primary !shadow-none !ring-0"
                                            />
                                        </div>
                                        {fieldState.invalid && (
                                            <FieldError errors={[fieldState.error]} />
                                        )}
                                    </Field>
                                )}
                            />
                        </FieldGroup>
                        <FieldGroup className="mb-4">
                            <Controller
                                name="password"
                                control={form.control}
                                render={({ field, fieldState }) => (
                                    <Field data-invalid={fieldState.invalid} className={cn('gap-1')}>
                                        <div className="icon-field relative">
                                            <Lock className="absolute start-5 top-1/2 transform -translate-y-1/2 w-5 h-5 text-neutral-700 dark:text-neutral-200" />
                                            <Input
                                                {...field}
                                                type={showPassword ? 'text' : 'password'}
                                                aria-invalid={fieldState.invalid}
                                                disabled={isSubmitting}
                                                placeholder="Password"
                                                name="password"
                                                autoComplete="off"
                                                className="ps-13 pe-12 h-14 rounded-xl bg-neutral-100 dark:bg-slate-800 border border-neutral-300 dark:border-slate-700 focus:border-primary dark:focus:border-primary focus-visible:border-primary !shadow-none !ring-0"
                                            />
                                            <Button
                                                type="button"
                                                onClick={() => setShowPassword(!showPassword)}
                                                className="absolute right-4 top-1/2 transform -translate-y-1/2 !p-0 bg-transparent hover:bg-transparent text-muted-foreground h-[unset]"
                                            >
                                                {showPassword ? (
                                                    <EyeOff className="w-5 h-5" />
                                                ) : (
                                                    <Eye className="w-5 h-5" />
                                                )}
                                            </Button>
                                        </div>
                                        {fieldState.invalid && (
                                            <FieldError errors={[fieldState.error]} />
                                        )}
                                    </Field>
                                )}
                            />
                        </FieldGroup>

                        {/* Remember Me & Forgot Password */}
                        <div className="mt-2 flex justify-between items-center">
                            <div className="flex items-center gap-2">
                                <Checkbox
                                    id="remember"
                                    className="border border-neutral-400 w-4.5 h-4.5"
                                />
                                <label htmlFor="remember" className="text-sm">
                                    Remember me
                                </label>
                            </div>
                            <Link
                                to="/auth/forgot-password"
                                className="text-primary font-medium hover:underline text-sm"
                            >
                                Forgot Password?
                            </Link>
                        </div>

                        <Button
                            type="submit"
                            className="w-full rounded-lg h-[52px] text-sm mt-8"
                            disabled={isSubmitting}
                        >
                            {isLoading && <Loader2 className="animate-spin h-4.5 w-4.5 mr-2" />}
                            {isLoading ? "Signing in..." : "Sign In"}
                        </Button>

                        <div className="mt-8 center-border-horizontal text-center relative before:absolute before:w-full before:h-[1px] before:top-1/2 before:-translate-y-1/2 before:bg-neutral-300 before:start-0">
                            <span className="bg-white dark:bg-slate-900 z-[2] relative px-4">Or sign in with</span>
                        </div>
                        <SocialLogin />

                        <Button
                            className="font-semibold text-neutral-600 hover:text-neutral-600 dark:text-neutral-200 py-6 px-2 w-1/2 border border-neutral-600/50 rounded-xl text-sm flex items-center justify-center gap-3 line-height-1 hover:border-blue-400 hover:bg-primary/10 disabled:opacity-60 mt-4 w-full"
                            variant="outline"
                            type="button"
                            name="action"
                            value="google"
                            onClick={() => {
                                form.setValue("email", "wowdash@gmail.com");
                                form.setValue("password", "123456");
                            }}
                        >
                            Use Demo Credentials
                        </Button>


                        <div className="mt-8 text-center text-sm">
                            <p className="mb-0">Don't have an account? <Link to="/auth/register" className="text-primary font-semibold hover:underline">Sign Up</Link></p>
                        </div>
                    </form>
                </div>
            </div>
        </section>
    );
};

export default Login;