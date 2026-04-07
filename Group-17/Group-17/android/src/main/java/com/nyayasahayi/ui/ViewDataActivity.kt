package com.nyayasahayi.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.nyayasahayi.R
import com.nyayasahayi.data.AppDatabase
import com.nyayasahayi.data.LocalClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class ViewDataActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_view_data)

        val recyclerView = findViewById<RecyclerView>(R.id.recycler_view_data)
        recyclerView.layoutManager = LinearLayoutManager(this)

        lifecycleScope.launch(Dispatchers.IO) {
            val db = AppDatabase.getDatabase(applicationContext)
            // Fetch all clients
            val clients = db.appDao().getAllClients()
            // For each client, fetch cases (inefficient N+1 but fine for small local DB/demo)
            val fullData = clients.map { client ->
                val cases = db.appDao().getCasesForClient(client.id)
                ClientWithCases(client, cases)
            }

            withContext(Dispatchers.Main) {
                recyclerView.adapter = DataAdapter(fullData)
            }
        }
    }
}

data class ClientWithCases(val client: LocalClient, val cases: List<com.nyayasahayi.data.LocalCase>)

class DataAdapter(private val dataList: List<ClientWithCases>) : RecyclerView.Adapter<DataAdapter.ViewHolder>() {

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val tvName: TextView = view.findViewById(R.id.tv_item_name)
        val tvPhone: TextView = view.findViewById(R.id.tv_item_phone)
        val tvDetails: TextView = view.findViewById(R.id.tv_item_details)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context).inflate(R.layout.item_data_view, parent, false)
        return ViewHolder(view)
    }

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = dataList[position]
        holder.tvName.text = item.client.name
        holder.tvPhone.text = item.client.phoneNumber
        
        val caseText = if (item.cases.isEmpty()) {
            "No Linked Cases"
        } else {
            item.cases.joinToString("\n\n") { 
                "• CNR: ${it.cnrNumber}\n  Status: ${it.status ?: "N/A"}\n  Next Date: ${it.nextDate ?: "N/A"}" 
            }
        }
        holder.tvDetails.text = caseText
    }

    override fun getItemCount() = dataList.size
}
