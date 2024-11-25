// path: frontend/src/app/api/ac/temperature/route.ts
import { NextResponse } from 'next/server'
import axios from 'axios'
import { API_BASE_URL } from '../constants'

export async function POST(request: Request) {
  try {
    const { temperature } = await request.json()

    // 온도 범위 검증 (18-30도)
    if (temperature < 18 || temperature > 30) {
      return NextResponse.json(
        { error: 'Temperature must be between 18°C and 30°C' },
        { status: 400 }
      )
    }

    const { data } = await axios.post(API_BASE_URL + '/temperature', { temperature })
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error updating temperature:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error occurred' },
      { status: 500 }
    )
  }
}