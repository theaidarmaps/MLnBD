type Prediction = {
  insult: number
  normal: number
  obscenity: number
  threat: number
}

export interface Data {
  isToxic: boolean
  predictions: Prediction
  text: string
}
