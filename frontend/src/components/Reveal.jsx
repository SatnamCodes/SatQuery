import { motion } from "framer-motion";

export default function Reveal({ children, delay = 0, className = "", as = "div" }) {
  const MotionTag = motion[as] ?? motion.div;
  return (
    <MotionTag
      className={className}
      initial={{ opacity: 0, y: 28 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.3 }}
      transition={{ type: "spring", stiffness: 300, damping: 25, delay }}
    >
      {children}
    </MotionTag>
  );
}
