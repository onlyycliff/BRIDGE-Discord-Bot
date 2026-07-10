import { motion } from "framer-motion"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function WorkshopSchedule() {
  return (
    <motion.div
      className="space-y-4"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.25 }}
    >
      <h1 className="text-2xl font-bold">Workshop Schedule</h1>
      <Card>
        <CardHeader>
          <CardTitle>Schedule</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Workshop schedule and overview will render here.</p>
        </CardContent>
      </Card>
    </motion.div>
  )
}
