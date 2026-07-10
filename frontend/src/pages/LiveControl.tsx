import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function LiveControl() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">Live Control</h1>
      <Card>
        <CardHeader>
          <CardTitle>Create Poll</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">Poll creation form and active poll management will render here.</p>
        </CardContent>
      </Card>
    </div>
  )
}
