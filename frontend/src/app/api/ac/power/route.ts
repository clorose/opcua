// path: frontend/src/app/api/ac/power/route.ts
import { NextResponse } from 'next/server'
import axios from 'axios'
import { API_BASE_URL } from '../constants'

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const { data } = await axios.post(API_BASE_URL + '/power', body)
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error updating power state:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Unknown error occurred' },
      { status: 500 }
    )
  }
}