import AuthImage from "@/assets/images/auth/forgot-pass-img.png";
import ThemeLogo from "@/components/shared/ThemeLogo";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useIsSubmitting } from "@/context/isSubmittingContext";
import { sendPasswordReset } from "@/firebase";
import { Loader2, Mail } from 'lucide-react';
import { Link, useNavigate } from "react-router-dom";
import { toast } from 'react-toastify';

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
});


const ForgotPassword = () => {
    const navigate = useNavigate();
    const { isSubmitting, setIsSubmitting } = useIsSubmitting();

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            email: "",
        },
    });


    const handleResetPassword = async (data: z.infer<typeof formSchema>) => {
        setIsSubmitting(true);

        const result = await sendPasswordReset(data.email);

        if (result.success) {
            toast.success("Email sent! Please check your email inbox or spam.");
            navigate('/auth/login')
        } else {
            toast.error(result.message);
        }

        setIsSubmitting(false);
        form.reset();
    };

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
                        <h4 className="mb-3"> Forgot Password </h4>
                        <p className="mb-8 text-secondary-light text-lg">Enter the email address associated with your account and we will send you a link to reset your password.</p>
                    </div>



                    <form action="#" onSubmit={form.handleSubmit(handleResetPassword)}>
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

                        <Button
                            type="submit"
                            className="w-full rounded-lg h-[52px] text-sm mt-4"
                            disabled={isSubmitting}
                        >
                            {isSubmitting && <Loader2 className="animate-spin h-4.5 w-4.5 mr-2" />}
                            {isSubmitting ? "Sending Recovery Email..." : "Send Recovery Email"}
                        </Button>

                        <div className="mt-8 text-center text-sm">
                            <p className="mb-0"> Remembered your password? {" "} <Link to="/auth/login" className="text-primary font-semibold hover:underline">Back to Sign In</Link></p>
                        </div>
                    </form>
                </div>
            </div>
        </section>
    );
};

export default ForgotPassword;